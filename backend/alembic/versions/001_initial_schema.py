"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id'), nullable=False, unique=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('segments', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'call_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id'), nullable=False, unique=True),
        sa.Column('performance_score', sa.Float(), nullable=True),
        sa.Column('communication_clarity', sa.Float(), nullable=True),
        sa.Column('responsiveness', sa.Float(), nullable=True),
        sa.Column('objection_handling_score', sa.Float(), nullable=True),
        sa.Column('listening_ratio', sa.Float(), nullable=True),
        sa.Column('performance_explanation', sa.Text(), nullable=True),
        sa.Column('interest_level', sa.String(50), nullable=True),
        sa.Column('buying_signals_detected', postgresql.JSON(), nullable=True),
        sa.Column('sentiment_progression', postgresql.JSON(), nullable=True),
        sa.Column('conversion_likelihood', sa.Float(), nullable=True),
        sa.Column('call_reason', sa.String(50), nullable=True),
        sa.Column('call_reason_confidence', sa.Float(), nullable=True),
        sa.Column('call_outcome', sa.String(50), nullable=True),
        sa.Column('call_outcome_confidence', sa.Float(), nullable=True),
        sa.Column('products_discussed', postgresql.JSON(), nullable=True),
        sa.Column('recommended_products', postgresql.JSON(), nullable=True),
        sa.Column('objections_detected', postgresql.JSON(), nullable=True),
        sa.Column('missed_opportunities', postgresql.JSON(), nullable=True),
        sa.Column('missed_opportunity_flag', sa.Boolean(), default=False),
        sa.Column('agent_speaking_time', sa.Float(), nullable=True),
        sa.Column('customer_speaking_time', sa.Float(), nullable=True),
        sa.Column('time_to_first_pitch', sa.Float(), nullable=True),
        sa.Column('objection_handling_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'action_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('priority', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('action_items')
    op.drop_table('call_analyses')
    op.drop_table('transcripts')
    op.drop_table('calls')
    op.drop_table('products')
    op.drop_table('agents')

