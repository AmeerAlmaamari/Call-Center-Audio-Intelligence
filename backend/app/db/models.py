import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


class CallStatus(str, PyEnum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class CallOutcome(str, PyEnum):
    SUCCESSFUL_SALE = "successful_sale"
    INTERESTED_NOT_CONVERTED = "interested_not_converted"
    NOT_INTERESTED = "not_interested"
    SUPPORT_COMPLAINT = "support_complaint"
    UNKNOWN = "unknown"


class InterestLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class CallReason(str, PyEnum):
    PRODUCT_INQUIRY = "product_inquiry"
    PRICING_QUESTION = "pricing_question"
    COMPLAINT_SUPPORT = "complaint_support"
    FOLLOWUP_RENEWAL = "followup_renewal"
    OTHER = "other"


class ObjectionType(str, PyEnum):
    PRICE = "price"
    FEATURES = "features"
    TRUST = "trust"
    TIMING = "timing"
    OTHER = "other"


class ActionItemPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionItemCategory(str, PyEnum):
    FOLLOWUP = "followup"
    TRAINING = "training"
    COACHING = "coaching"
    OTHER = "other"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    calls = relationship("Call", back_populates="agent")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    status = Column(String(50), default=CallStatus.PENDING.value)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="calls")
    transcript = relationship("Transcript", back_populates="call", uselist=False)
    analysis = relationship("CallAnalysis", back_populates="call", uselist=False)
    action_items = relationship("ActionItem", back_populates="call")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False, unique=True)
    raw_text = Column(Text, nullable=False)
    segments = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="transcript")


class CallAnalysis(Base):
    __tablename__ = "call_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False, unique=True)

    # Employee Performance
    performance_score = Column(Float, nullable=True)
    communication_clarity = Column(Float, nullable=True)
    responsiveness = Column(Float, nullable=True)
    objection_handling_score = Column(Float, nullable=True)
    listening_ratio = Column(Float, nullable=True)
    performance_explanation = Column(Text, nullable=True)

    # Customer Buying Potential
    interest_level = Column(String(50), default=InterestLevel.UNKNOWN.value)
    buying_signals_detected = Column(JSON, nullable=True)
    sentiment_progression = Column(JSON, nullable=True)
    conversion_likelihood = Column(Float, nullable=True)

    # Call Classification
    call_reason = Column(String(50), default=CallReason.OTHER.value)
    call_reason_confidence = Column(Float, nullable=True)
    call_outcome = Column(String(50), default=CallOutcome.UNKNOWN.value)
    call_outcome_confidence = Column(Float, nullable=True)

    # Products
    products_discussed = Column(JSON, nullable=True)
    recommended_products = Column(JSON, nullable=True)

    # Sales Intelligence
    objections_detected = Column(JSON, nullable=True)
    missed_opportunities = Column(JSON, nullable=True)
    missed_opportunity_flag = Column(Boolean, default=False)

    # Operational Metrics
    agent_speaking_time = Column(Float, nullable=True)
    customer_speaking_time = Column(Float, nullable=True)
    time_to_first_pitch = Column(Float, nullable=True)
    objection_handling_time = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    call = relationship("Call", back_populates="analysis")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False)
    category = Column(String(50), default=ActionItemCategory.OTHER.value)
    priority = Column(String(50), default=ActionItemPriority.MEDIUM.value)
    description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    call = relationship("Call", back_populates="action_items")
