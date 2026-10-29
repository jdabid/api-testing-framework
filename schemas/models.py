"""Strict Pydantic v2 schemas for validating API responses and contracts."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class TokenResponseSchema(BaseModel):
    """Contract for JWT authentication response."""

    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(..., min_length=20)
    token_type: Literal["Bearer"]
    expires_in: int = Field(..., gt=0, le=86400)
    role: Literal["admin", "qa_engineer", "viewer"]


class TaskItemSchema(BaseModel):
    """Contract for an individual automation/transcoding task resource."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    title: str = Field(..., min_length=3, max_length=120)
    codec: Literal["h264", "prores_422", "openexr", "vp9"]
    priority: int = Field(..., ge=1, le=10)
    status: Literal["queued", "processing", "completed", "failed"]
    owner: str = Field(..., min_length=2)
    created_at: datetime


class PaginatedTasksSchema(BaseModel):
    """Contract for paginated GET /api/v1/tasks responses."""

    model_config = ConfigDict(extra="forbid")

    items: List[TaskItemSchema]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)


class ErrorResponseSchema(BaseModel):
    """Contract for standardized API error responses."""

    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(..., min_length=3)
    message: str = Field(..., min_length=5)
    details: Optional[str] = None

