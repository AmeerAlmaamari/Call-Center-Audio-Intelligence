from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    name: str
    email: Optional[str] = None
    department: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


class CallBase(BaseModel):
    filename: str
    agent_id: Optional[UUID] = None


class CallResponse(BaseModel):
    id: UUID
    filename: str
    file_path: str
    file_size: Optional[int] = None
    duration_seconds: Optional[float] = None
    status: str
    agent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    items: List[CallResponse]
    total: int
    page: int
    page_size: int


class TranscriptResponse(BaseModel):
    id: UUID
    call_id: UUID
    raw_text: str
    segments: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CallAnalysisResponse(BaseModel):
    id: UUID
    call_id: UUID
    performance_score: Optional[float] = None
    communication_clarity: Optional[float] = None
    responsiveness: Optional[float] = None
    objection_handling_score: Optional[float] = None
    listening_ratio: Optional[float] = None
    performance_explanation: Optional[str] = None
    interest_level: Optional[str] = None
    buying_signals_detected: Optional[List[Any]] = None
    sentiment_progression: Optional[List[Any]] = None
    conversion_likelihood: Optional[float] = None
    call_reason: Optional[str] = None
    call_reason_confidence: Optional[float] = None
    call_outcome: Optional[str] = None
    call_outcome_confidence: Optional[float] = None
    products_discussed: Optional[List[Any]] = None
    recommended_products: Optional[List[Any]] = None
    objections_detected: Optional[List[Any]] = None
    missed_opportunities: Optional[List[Any]] = None
    missed_opportunity_flag: bool = False
    agent_speaking_time: Optional[float] = None
    customer_speaking_time: Optional[float] = None
    time_to_first_pitch: Optional[float] = None
    objection_handling_time: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActionItemResponse(BaseModel):
    id: UUID
    call_id: UUID
    category: Optional[str] = None
    priority: Optional[str] = None
    description: str
    is_completed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardOverview(BaseModel):
    total_calls: int
    analyzed_calls: int
    conversion_rate: float
    avg_performance_score: Optional[float] = None
    avg_sentiment: Optional[float] = None
    outcome_distribution: dict


class CallInsights(BaseModel):
    top_call_reasons: List[dict]
    top_products: List[dict]
    buying_intent_distribution: dict
    common_objections: List[dict]


class AgentPerformance(BaseModel):
    agent_id: UUID
    agent_name: str
    total_calls: int
    avg_performance_score: Optional[float] = None
    avg_objection_handling: Optional[float] = None
    conversion_rate: float


class ActionCenterData(BaseModel):
    pending_followups: List[ActionItemResponse]
    missed_opportunities: List[dict]
    coaching_recommendations: List[ActionItemResponse]
    training_needs: dict


class TranscribeRequest(BaseModel):
    pass


class AnalyzeRequest(BaseModel):
    pass


class MessageResponse(BaseModel):
    message: str
    call_id: Optional[UUID] = None
