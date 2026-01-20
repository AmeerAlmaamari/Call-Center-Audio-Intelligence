import logging
import asyncio
import base64
import time
import httpx
from pathlib import Path
from backend.app.config import get_settings
from backend.app.utils.error_handling import (
    TranscriptionError,
    AudioValidationError,
    RateLimitError,
    AudioValidator,
    TranscriptValidator,
    retry_with_backoff,
    log_request,
    log_response,
)

logger = logging.getLogger(__name__)
settings = get_settings()

REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"


async def _make_replicate_request(client: httpx.AsyncClient, url: str, headers: dict, payload: dict = None) -> dict:
    """Make a request to Replicate API with rate limit handling."""
    try:
        if payload:
            response = await client.post(url, json=payload, headers=headers)
        else:
            response = await client.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", 60)
            raise RateLimitError(f"Replicate API rate limit exceeded", retry_after=int(retry_after))
        
        response.raise_for_status()
        return response.json()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitError("Replicate API rate limit exceeded")
        raise TranscriptionError(
            f"Replicate API error: {e.response.status_code} - {e.response.text}",
            status_code=e.response.status_code,
            retryable=e.response.status_code in (500, 502, 503, 504)
        )


async def transcribe_audio(audio_path: str, language: str = "auto") -> dict:
    """
    Transcribe audio using Replicate's openai/whisper model.
    Returns dict with 'text', 'segments', and validation metadata.
    
    Args:
        audio_path: Path to the audio file
        language: Language code or "auto" for automatic detection
    """
    start_time = time.time()
    
    if not settings.REPLICATE_API_KEY:
        raise TranscriptionError("REPLICATE_API_KEY not configured", status_code=500)

    # Validate audio file
    is_valid, error_msg, metadata = await AudioValidator.validate_audio_file(audio_path)
    if not is_valid:
        raise AudioValidationError(error_msg)
    
    logger.info(f"Starting transcription for {metadata['filename']} ({metadata['file_size_bytes']} bytes)")
    
    file_path = Path(audio_path)
    headers = {
        "Authorization": f"Bearer {settings.REPLICATE_API_KEY}",
        "Content-Type": "application/json",
    }

    # Read and encode audio file
    try:
        with open(file_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode("utf-8")
            audio_uri = f"data:audio/{file_path.suffix[1:]};base64,{audio_data}"
    except IOError as e:
        raise AudioValidationError(f"Failed to read audio file: {e}")

    # Determine language setting
    language_setting = None if language == "auto" else language

    payload = {
        "version": "4d50797290df275329f202e48c76360b3f22b08d28c196cbc54600319435f8d2",
        "input": {
            "audio": audio_uri,
            "model": "large-v3",
            "translate": False,
            "temperature": 0,
            "transcription": "plain text",
            "suppress_tokens": "-1",
            "logprob_threshold": -1,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": True,
            "compression_ratio_threshold": 2.4,
        },
    }
    
    # Add language if specified
    if language_setting:
        payload["input"]["language"] = language_setting

    log_request("transcribe_audio", {"file": metadata["filename"], "language": language})

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit transcription job with retry
        prediction = await retry_with_backoff(
            _make_replicate_request,
            client, REPLICATE_API_URL, headers, payload,
            max_retries=3,
            base_delay=2.0
        )

        prediction_url = prediction.get("urls", {}).get("get")
        if not prediction_url:
            raise TranscriptionError("No prediction URL returned from Replicate")

        # Poll for completion with timeout
        max_polls = 120
        poll_interval = 5
        
        for poll_count in range(max_polls):
            await asyncio.sleep(poll_interval)
            
            try:
                status_data = await retry_with_backoff(
                    _make_replicate_request,
                    client, prediction_url, headers,
                    max_retries=2,
                    base_delay=1.0
                )
            except Exception as e:
                logger.warning(f"Poll {poll_count + 1} failed: {e}")
                continue

            status = status_data.get("status")
            
            if status == "succeeded":
                output = status_data.get("output", {})
                
                # Parse output based on format
                if isinstance(output, str):
                    transcript_text = output
                    segments = []
                else:
                    transcript_text = output.get("transcription", output.get("text", ""))
                    segments = output.get("segments", [])
                
                # Validate transcript
                is_valid, warning, transcript_meta = TranscriptValidator.validate_transcript(transcript_text)
                
                duration_ms = (time.time() - start_time) * 1000
                
                result = {
                    "text": transcript_text,
                    "segments": segments,
                    "detected_language": output.get("detected_language") if isinstance(output, dict) else None,
                    "validation": {
                        "is_valid": is_valid,
                        "warning": warning,
                        **transcript_meta
                    }
                }
                
                log_response("transcribe_audio", {
                    "text_length": len(transcript_text),
                    "segments": len(segments),
                    "warning": warning
                }, duration_ms)
                
                if warning:
                    logger.warning(f"Transcription warning for {metadata['filename']}: {warning}")
                
                return result
                
            elif status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                raise TranscriptionError(f"Transcription failed: {error_msg}")
            
            elif status == "canceled":
                raise TranscriptionError("Transcription was canceled")
            
            # Log progress periodically
            if poll_count > 0 and poll_count % 12 == 0:
                logger.info(f"Transcription in progress... ({poll_count * poll_interval}s elapsed)")

        raise TranscriptionError(
            f"Transcription timed out after {max_polls * poll_interval} seconds",
            retryable=True
        )
