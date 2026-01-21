import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.db.models import Agent, Call, CallAnalysis, CallStatus
from backend.app.schemas import AgentResponse, AgentCreate, AgentUpdate, AgentPerformance, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all agents."""
    result = await db.execute(select(Agent).order_by(Agent.name))
    return result.scalars().all()


@router.post("", response_model=AgentResponse)
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new agent."""
    agent = Agent(
        id=uuid.uuid4(),
        name=agent_data.name,
        email=agent_data.email,
        department=agent_data.department,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/performance", response_model=AgentPerformance)
async def get_agent_performance(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get performance metrics for an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    calls_result = await db.execute(
        select(Call).where(Call.agent_id == agent_id)
    )
    calls = calls_result.scalars().all()
    total_calls = len(calls)

    if total_calls == 0:
        return AgentPerformance(
            agent_id=agent_id,
            agent_name=agent.name,
            total_calls=0,
            avg_performance_score=None,
            avg_objection_handling=None,
            avg_conversion_likelihood=None,
            conversion_rate=0.0,
            successful_sales=0,
        )

    call_ids = [c.id for c in calls]
    analyses_result = await db.execute(
        select(CallAnalysis).where(CallAnalysis.call_id.in_(call_ids))
    )
    analyses = analyses_result.scalars().all()

    performance_scores = [a.performance_score for a in analyses if a.performance_score is not None]
    objection_scores = [a.objection_handling_score for a in analyses if a.objection_handling_score is not None]
    conversion_scores = [a.conversion_likelihood for a in analyses if a.conversion_likelihood is not None]
    
    successful_sales = sum(
        1 for a in analyses 
        if a.call_outcome and a.call_outcome == "successful_sale"
    )

    return AgentPerformance(
        agent_id=agent_id,
        agent_name=agent.name,
        total_calls=total_calls,
        avg_performance_score=round(sum(performance_scores) / len(performance_scores), 2) if performance_scores else None,
        avg_objection_handling=round(sum(objection_scores) / len(objection_scores), 2) if objection_scores else None,
        avg_conversion_likelihood=round(sum(conversion_scores) / len(conversion_scores), 2) if conversion_scores else None,
        conversion_rate=round((successful_sales / total_calls * 100), 2) if total_calls > 0 else 0.0,
        successful_sales=successful_sales,
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    agent.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", response_model=MessageResponse)
async def delete_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete an agent. Calls assigned to this agent will be unassigned."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Unassign calls from this agent
    await db.execute(
        Call.__table__.update().where(Call.agent_id == agent_id).values(agent_id=None)
    )

    await db.delete(agent)
    await db.commit()

    return MessageResponse(message=f"Agent '{agent.name}' deleted successfully")
