import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from mutagen import File as MutagenFile

from backend.app.db.database import get_db, async_session_factory
from backend.app.db.models import Call, Transcript, CallAnalysis, ActionItem, Product, CallStatus, Agent
from backend.app.utils.error_handling import (
    AudioValidator,
    AudioValidationError,
    TranscriptionError,
    AnalysisError,
)
from backend.app.schemas import (
    CallResponse,
    CallListResponse,
    TranscriptResponse,
    CallAnalysisResponse,
    ActionItemResponse,
    MessageResponse,
)
from backend.app.services.transcription import transcribe_audio
from backend.app.services.analysis import run_full_analysis

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def validate_audio_file(filename: str, file_size: int):
    """Validate uploaded audio file using AudioValidator."""
    # Check extension
    if not AudioValidator.validate_file_extension(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(AudioValidator.SUPPORTED_FORMATS)}",
        )
    
    # Check file size
    is_valid, error_msg = AudioValidator.validate_file_size(file_size)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)


def get_audio_duration(file_path: str) -> Optional[float]:
    """Extract duration from audio file using mutagen."""
    try:
        audio = MutagenFile(file_path)
        if audio is not None and audio.info is not None:
            return audio.info.length
    except Exception as e:
        logger.warning(f"Could not extract audio duration: {e}")
    return None


@router.post("/upload", response_model=CallResponse)
async def upload_call(
    file: UploadFile = File(...),
    agent_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an audio file for a new call. Agent ID is required."""
    content = await file.read()
    file_size = len(content)
    validate_audio_file(file.filename, file_size)

    # Validate agent_id
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id. Must be a UUID.",
        ) from exc

    # Verify agent exists
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found. Please select a valid agent.",
        )

    call_id = uuid.uuid4()
    ext = Path(file.filename).suffix.lower()
    stored_filename = f"{call_id}{ext}"
    file_path = UPLOAD_DIR / stored_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Extract audio duration
    duration_seconds = get_audio_duration(str(file_path))

    call = Call(
        id=call_id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        duration_seconds=duration_seconds,
        status=CallStatus.PENDING.value,
        agent_id=agent_uuid,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)

    logger.info(f"Uploaded call {call_id}: {file.filename} (duration: {duration_seconds}s, agent: {agent.name})")
    return call


@router.get("", response_model=CallListResponse)
async def list_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all calls with pagination."""
    query = select(Call)
    if status:
        query = query.where(Call.status == status)
    
    count_query = select(func.count()).select_from(Call)
    if status:
        count_query = count_query.where(Call.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Call.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    calls = result.scalars().all()

    return CallListResponse(
        items=[CallResponse.model_validate(c) for c in calls],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get call details by ID."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.delete("/{call_id}", response_model=MessageResponse)
async def delete_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a call and its associated data."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.file_path and os.path.exists(call.file_path):
        os.remove(call.file_path)

    await db.execute(select(ActionItem).where(ActionItem.call_id == call_id))
    await db.execute(select(CallAnalysis).where(CallAnalysis.call_id == call_id))
    await db.execute(select(Transcript).where(Transcript.call_id == call_id))

    await db.delete(call)
    await db.commit()

    return MessageResponse(message="Call deleted successfully", call_id=call_id)


@router.get("/{call_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get transcript for a call."""
    result = await db.execute(select(Transcript).where(Transcript.call_id == call_id))
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.get("/{call_id}/analysis", response_model=CallAnalysisResponse)
async def get_analysis(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get analysis for a call."""
    result = await db.execute(select(CallAnalysis).where(CallAnalysis.call_id == call_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/{call_id}/actions", response_model=list[ActionItemResponse])
async def get_action_items(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get action items for a call."""
    result = await db.execute(select(ActionItem).where(ActionItem.call_id == call_id))
    return result.scalars().all()


@router.post("/{call_id}/transcribe", response_model=MessageResponse)
async def transcribe_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Trigger transcription for a call."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status not in [CallStatus.PENDING.value, CallStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Call cannot be transcribed in status: {call.status}",
        )

    call.status = CallStatus.TRANSCRIBING.value
    await db.commit()

    try:
        result_data = await transcribe_audio(call.file_path)
        
        transcript = Transcript(
            id=uuid.uuid4(),
            call_id=call_id,
            raw_text=result_data.get("text", ""),
            segments=result_data.get("segments", []),
            created_at=datetime.utcnow(),
        )
        db.add(transcript)
        
        call.status = CallStatus.TRANSCRIBED.value
        await db.commit()

        logger.info(f"Transcription completed for call {call_id}")
        return MessageResponse(message="Transcription completed", call_id=call_id)

    except Exception as e:
        logger.error(f"Transcription failed for call {call_id}: {e}")
        call.status = CallStatus.FAILED.value
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/{call_id}/analyze", response_model=MessageResponse)
async def analyze_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Trigger full analysis for a call."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    transcript_result = await db.execute(select(Transcript).where(Transcript.call_id == call_id))
    transcript = transcript_result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=400, detail="Call must be transcribed first")

    if call.status not in [CallStatus.TRANSCRIBED.value, CallStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Call cannot be analyzed in status: {call.status}",
        )

    call.status = CallStatus.ANALYZING.value
    await db.commit()

    try:
        products_result = await db.execute(select(Product.name))
        product_names = [p[0] for p in products_result.all()]

        analysis_data = await run_full_analysis(transcript.raw_text, product_names)
        action_items_data = analysis_data.pop("action_items", [])

        existing_analysis = await db.execute(
            select(CallAnalysis).where(CallAnalysis.call_id == call_id)
        )
        existing = existing_analysis.scalar_one_or_none()
        
        if existing:
            for key, value in analysis_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
        else:
            analysis = CallAnalysis(
                id=uuid.uuid4(),
                call_id=call_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **{k: v for k, v in analysis_data.items() if hasattr(CallAnalysis, k)},
            )
            db.add(analysis)

        await db.execute(select(ActionItem).where(ActionItem.call_id == call_id))
        
        for item_data in action_items_data:
            action_item = ActionItem(
                id=uuid.uuid4(),
                call_id=call_id,
                category=item_data.get("category", "other"),
                priority=item_data.get("priority", "medium"),
                description=item_data.get("description", ""),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(action_item)

        call.status = CallStatus.ANALYZED.value
        await db.commit()

        logger.info(f"Analysis completed for call {call_id}")
        return MessageResponse(message="Analysis completed", call_id=call_id)

    except Exception as e:
        logger.error(f"Analysis failed for call {call_id}: {e}")
        call.status = CallStatus.FAILED.value
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def process_call_pipeline(call_id: uuid.UUID):
    """Background task to run full pipeline: transcribe -> analyze."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(select(Call).where(Call.id == call_id))
            call = result.scalar_one_or_none()
            if not call:
                logger.error(f"Call {call_id} not found for pipeline processing")
                return

            # Step 1: Transcription
            logger.info(f"Pipeline: Starting transcription for call {call_id}")
            call.status = CallStatus.TRANSCRIBING.value
            await db.commit()

            try:
                result_data = await transcribe_audio(call.file_path)
                
                transcript = Transcript(
                    id=uuid.uuid4(),
                    call_id=call_id,
                    raw_text=result_data.get("text", ""),
                    segments=result_data.get("segments", []),
                    created_at=datetime.utcnow(),
                )
                db.add(transcript)
                call.status = CallStatus.TRANSCRIBED.value
                await db.commit()
                logger.info(f"Pipeline: Transcription completed for call {call_id}")

            except Exception as e:
                logger.error(f"Pipeline: Transcription failed for call {call_id}: {e}")
                call.status = CallStatus.FAILED.value
                await db.commit()
                return

            # Step 2: Analysis
            logger.info(f"Pipeline: Starting analysis for call {call_id}")
            call.status = CallStatus.ANALYZING.value
            await db.commit()

            try:
                transcript_result = await db.execute(
                    select(Transcript).where(Transcript.call_id == call_id)
                )
                transcript = transcript_result.scalar_one_or_none()

                products_result = await db.execute(select(Product.name))
                product_names = [p[0] for p in products_result.all()]

                analysis_data = await run_full_analysis(transcript.raw_text, product_names)
                action_items_data = analysis_data.pop("action_items", [])

                analysis = CallAnalysis(
                    id=uuid.uuid4(),
                    call_id=call_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    **{k: v for k, v in analysis_data.items() if hasattr(CallAnalysis, k)},
                )
                db.add(analysis)

                for item_data in action_items_data:
                    action_item = ActionItem(
                        id=uuid.uuid4(),
                        call_id=call_id,
                        category=item_data.get("category", "other"),
                        priority=item_data.get("priority", "medium"),
                        description=item_data.get("description", ""),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(action_item)

                call.status = CallStatus.ANALYZED.value
                await db.commit()
                logger.info(f"Pipeline: Analysis completed for call {call_id}")

            except Exception as e:
                logger.error(f"Pipeline: Analysis failed for call {call_id}: {e}")
                call.status = CallStatus.FAILED.value
                await db.commit()
                return

            logger.info(f"Pipeline: Full processing completed for call {call_id}")

        except Exception as e:
            logger.error(f"Pipeline: Unexpected error for call {call_id}: {e}")


@router.post("/{call_id}/process", response_model=MessageResponse)
async def process_call(
    call_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger full processing pipeline (transcribe + analyze) as background task."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status not in [CallStatus.PENDING.value, CallStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Call cannot be processed in status: {call.status}. Only 'pending' or 'failed' calls can be processed.",
        )

    call.status = CallStatus.TRANSCRIBING.value
    await db.commit()

    background_tasks.add_task(process_call_pipeline, call_id)

    logger.info(f"Started background processing for call {call_id}")
    return MessageResponse(
        message="Processing started. Poll the call status for updates.",
        call_id=call_id
    )


@router.get("/{call_id}/status")
async def get_call_status(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get current processing status for a call (for polling)."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    has_transcript = False
    has_analysis = False
    action_items_count = 0

    if call.status in [CallStatus.TRANSCRIBED.value, CallStatus.ANALYZING.value, CallStatus.ANALYZED.value]:
        transcript_result = await db.execute(
            select(Transcript.id).where(Transcript.call_id == call_id)
        )
        has_transcript = transcript_result.scalar_one_or_none() is not None

    if call.status == CallStatus.ANALYZED.value:
        analysis_result = await db.execute(
            select(CallAnalysis.id).where(CallAnalysis.call_id == call_id)
        )
        has_analysis = analysis_result.scalar_one_or_none() is not None

        action_count_result = await db.execute(
            select(func.count(ActionItem.id)).where(ActionItem.call_id == call_id)
        )
        action_items_count = action_count_result.scalar() or 0

    return {
        "call_id": str(call_id),
        "status": call.status,
        "has_transcript": has_transcript,
        "has_analysis": has_analysis,
        "action_items_count": action_items_count,
        "is_processing": call.status in [CallStatus.TRANSCRIBING.value, CallStatus.ANALYZING.value],
        "is_complete": call.status == CallStatus.ANALYZED.value,
        "is_failed": call.status == CallStatus.FAILED.value,
    }
