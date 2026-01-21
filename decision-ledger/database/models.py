"""Database models (Pydantic schemas)."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class Dataset(BaseModel):
    """Dataset model."""
    dataset_id: str
    filename: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    rows: int
    columns: int
    schema: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None


class Forecast(BaseModel):
    """Forecast model."""
    forecast_id: str
    dataset_id: str
    model_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    horizon: int
    predictions: List[Dict[str, Any]]
    metrics: Optional[Dict[str, float]] = None


class Decision(BaseModel):
    """Decision model."""
    decision_id: str
    title: str
    description: Optional[str] = None
    forecast_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    predicted_outcome: Optional[Dict[str, Any]] = None
    decision_rationale: Optional[str] = None
    tags: Optional[List[str]] = None


class Outcome(BaseModel):
    """Outcome model."""
    outcome_id: str
    decision_id: str
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    actual_outcome: Dict[str, Any]
    notes: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    message_id: str
    session_id: str
    role: str  # user or assistant
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
