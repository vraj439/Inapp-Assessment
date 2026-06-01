from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TENTATIVE = "tentative"


class InvitationCreate(BaseModel):
    event_series_id: UUID
    invitee_id: UUID
    invited_by: UUID
    occurrence_start: datetime | None = Field(
        default=None,
        description="Null = series-wide invitation; set for single-occurrence invite",
    )


class InvitationStatusUpdate(BaseModel):
    status: InvitationStatus
    response_message: str | None = Field(default=None, max_length=500)


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_series_id: UUID
    invitee_id: UUID
    occurrence_start: datetime | None
    status: InvitationStatus
    invited_by: UUID
    created_at: datetime
    updated_at: datetime
    response_message: str | None


class InvitationListResponse(BaseModel):
    items: list[InvitationResponse]
    total: int
