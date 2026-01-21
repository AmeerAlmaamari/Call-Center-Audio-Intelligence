import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.database import get_db
from backend.app.db.models import (
    Call, CallAnalysis, ActionItem, Agent, CallStatus,
    CallOutcome, CallReason, InterestLevel, ActionItemCategory,
)
from backend.app.schemas import (
    DashboardOverview,
    RecentCallResponse,
    CallInsights,
    AgentPerformance,
    ActionCenterData,
    ActionItemResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Get executive overview dashboard data."""
    total_result = await db.execute(select(func.count()).select_from(Call))
    total_calls = total_result.scalar() or 0

    analyzed_result = await db.execute(
        select(func.count()).select_from(Call).where(Call.status == CallStatus.ANALYZED.value)
    )
    analyzed_calls = analyzed_result.scalar() or 0

    # Calls today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count()).select_from(Call).where(Call.created_at >= today_start)
    )
    calls_today = today_result.scalar() or 0

    # Get all analyses
    analyses_result = await db.execute(select(CallAnalysis))
    analyses = analyses_result.scalars().all()

    successful_sales = sum(
        1 for a in analyses
        if a.call_outcome and a.call_outcome == "successful_sale"
    )
    conversion_rate = (successful_sales / analyzed_calls * 100) if analyzed_calls > 0 else 0.0

    performance_scores = [a.performance_score for a in analyses if a.performance_score is not None]
    avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else None

    conversion_scores = [a.conversion_likelihood for a in analyses if a.conversion_likelihood is not None]
    avg_conversion_likelihood = sum(conversion_scores) / len(conversion_scores) if conversion_scores else None

    # Calls by status
    calls_by_status = {}
    for status in CallStatus:
        count_result = await db.execute(
            select(func.count()).select_from(Call).where(Call.status == status.value)
        )
        count = count_result.scalar() or 0
        if count > 0:
            calls_by_status[status.value] = count

    # Calls by outcome (from analyses)
    calls_by_outcome = {}
    for outcome in CallOutcome:
        count = sum(1 for a in analyses if a.call_outcome and a.call_outcome == outcome.value)
        if count > 0:
            calls_by_outcome[outcome.value] = count

    outcome_distribution = {}
    for outcome in CallOutcome:
        count = sum(1 for a in analyses if a.call_outcome and a.call_outcome == outcome.value)
        outcome_distribution[outcome.value] = count

    # Recent calls with agent info
    recent_calls_result = await db.execute(
        select(Call)
        .options(selectinload(Call.agent))
        .order_by(Call.created_at.desc())
        .limit(10)
    )
    recent_calls_raw = recent_calls_result.scalars().all()
    recent_calls = [
        RecentCallResponse(
            id=c.id,
            filename=c.filename,
            status=c.status,
            agent_id=c.agent_id,
            agent_name=c.agent.name if c.agent else None,
            created_at=c.created_at,
            duration_seconds=c.duration_seconds,
        )
        for c in recent_calls_raw
    ]

    return DashboardOverview(
        total_calls=total_calls,
        analyzed_calls=analyzed_calls,
        calls_today=calls_today,
        conversion_rate=round(conversion_rate, 2),
        avg_performance_score=round(avg_performance, 2) if avg_performance else None,
        avg_conversion_likelihood=round(avg_conversion_likelihood, 2) if avg_conversion_likelihood else None,
        avg_sentiment=round(avg_conversion_likelihood, 2) if avg_conversion_likelihood else None,
        calls_by_status=calls_by_status,
        calls_by_outcome=calls_by_outcome,
        outcome_distribution=outcome_distribution,
        recent_calls=recent_calls,
    )


@router.get("/insights", response_model=CallInsights)
async def get_insights(db: AsyncSession = Depends(get_db)):
    """Get call insights aggregation."""
    analyses_result = await db.execute(select(CallAnalysis))
    analyses = analyses_result.scalars().all()

    reason_counts = {}
    for reason in CallReason:
        count = sum(1 for a in analyses if a.call_reason and a.call_reason == reason.value)
        if count > 0:
            reason_counts[reason.value] = count

    top_call_reasons = [
        {"reason": k, "count": v}
        for k, v in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    product_counts = {}
    for a in analyses:
        if a.products_discussed:
            for p in a.products_discussed:
                name = p.get("name", "Unknown") if isinstance(p, dict) else str(p)
                product_counts[name] = product_counts.get(name, 0) + 1

    top_products = [
        {"product": k, "count": v}
        for k, v in sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    intent_distribution = {}
    for level in InterestLevel:
        count = sum(1 for a in analyses if a.interest_level and a.interest_level == level.value)
        intent_distribution[level.value] = count

    objection_counts = {}
    for a in analyses:
        if a.objections_detected:
            for obj in a.objections_detected:
                obj_type = obj.get("type", "other") if isinstance(obj, dict) else "other"
                objection_counts[obj_type] = objection_counts.get(obj_type, 0) + 1

    common_objections = [
        {"type": k, "count": v}
        for k, v in sorted(objection_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return CallInsights(
        top_call_reasons=top_call_reasons,
        top_products=top_products,
        buying_intent_distribution=intent_distribution,
        common_objections=common_objections,
    )


@router.get("/agents", response_model=list[AgentPerformance])
async def get_agents_performance(db: AsyncSession = Depends(get_db)):
    """Get performance data for all agents."""
    agents_result = await db.execute(select(Agent))
    agents = agents_result.scalars().all()

    performance_list = []
    for agent in agents:
        calls_result = await db.execute(
            select(Call).where(Call.agent_id == agent.id)
        )
        calls = calls_result.scalars().all()
        total_calls = len(calls)

        if total_calls == 0:
            performance_list.append(AgentPerformance(
                agent_id=agent.id,
                agent_name=agent.name,
                total_calls=0,
                avg_performance_score=None,
                avg_objection_handling=None,
                conversion_rate=0.0,
            ))
            continue

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

        performance_list.append(AgentPerformance(
            agent_id=agent.id,
            agent_name=agent.name,
            total_calls=total_calls,
            avg_performance_score=round(sum(performance_scores) / len(performance_scores), 2) if performance_scores else None,
            avg_objection_handling=round(sum(objection_scores) / len(objection_scores), 2) if objection_scores else None,
            avg_conversion_likelihood=round(sum(conversion_scores) / len(conversion_scores), 2) if conversion_scores else None,
            conversion_rate=round(successful_sales / total_calls * 100, 2) if total_calls > 0 else 0.0,
            successful_sales=successful_sales,
        ))

    return sorted(performance_list, key=lambda x: x.avg_performance_score or 0, reverse=True)


@router.get("/actions", response_model=ActionCenterData)
async def get_action_center(db: AsyncSession = Depends(get_db)):
    """Get action center dashboard data."""
    followups_result = await db.execute(
        select(ActionItem)
        .where(ActionItem.category == ActionItemCategory.FOLLOWUP)
        .where(ActionItem.is_completed == False)
        .order_by(ActionItem.created_at.desc())
        .limit(20)
    )
    pending_followups = [
        ActionItemResponse.model_validate(a) for a in followups_result.scalars().all()
    ]

    analyses_result = await db.execute(
        select(CallAnalysis).where(CallAnalysis.missed_opportunity_flag == True)
    )
    missed_opps = []
    for a in analyses_result.scalars().all():
        if a.missed_opportunities:
            for opp in a.missed_opportunities:
                base = {"call_id": str(a.call_id)}
                if isinstance(opp, dict):
                    base.update(opp)
                else:
                    base["description"] = str(opp)
                missed_opps.append(base)

    coaching_result = await db.execute(
        select(ActionItem)
        .where(ActionItem.category == ActionItemCategory.COACHING)
        .where(ActionItem.is_completed == False)
        .order_by(ActionItem.created_at.desc())
        .limit(20)
    )
    coaching_recommendations = [
        ActionItemResponse.model_validate(a) for a in coaching_result.scalars().all()
    ]

    training_result = await db.execute(
        select(ActionItem)
        .where(ActionItem.category == ActionItemCategory.TRAINING)
        .where(ActionItem.is_completed == False)
    )
    training_items = training_result.scalars().all()
    
    training_needs = {}
    for item in training_items:
        desc_lower = item.description.lower()
        if "objection" in desc_lower:
            category = "objection_handling"
        elif "price" in desc_lower or "pricing" in desc_lower:
            category = "pricing"
        elif "product" in desc_lower:
            category = "product_knowledge"
        elif "communication" in desc_lower:
            category = "communication"
        else:
            category = "general"
        training_needs[category] = training_needs.get(category, 0) + 1

    return ActionCenterData(
        pending_followups=pending_followups,
        missed_opportunities=missed_opps[:20],
        coaching_recommendations=coaching_recommendations,
        training_needs=training_needs,
    )
