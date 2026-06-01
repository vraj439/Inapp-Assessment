"""Public API schemas exposed via API Gateway Swagger."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# --- Users ---


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


# --- Events ---


class RecurrenceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Weekday(str, Enum):
    MO = "MO"
    TU = "TU"
    WE = "WE"
    TH = "TH"
    FR = "FR"
    SA = "SA"
    SU = "SU"


class RecurrenceRule(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1, le=999)
    by_weekday: list[Weekday] | None = None
    by_monthday: list[int] | None = None
    until: datetime | None = None
    count: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def validate_end(self) -> "RecurrenceRule":
        if self.until and self.count:
            raise ValueError("Specify either until or count, not both")
        return self


class EditScope(str, Enum):
    SINGLE = "single"
    FUTURE = "future"
    ALL = "all"


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    organizer_id: UUID
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    location: str | None = None
    participant_ids: list[UUID] = Field(default_factory=list)
    recurrence_rule: RecurrenceRule | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    timezone: str | None = None
    location: str | None = None
    participant_ids: list[UUID] | None = None
    recurrence_rule: RecurrenceRule | None = None


class EventOccurrenceUpdate(BaseModel):
    scope: EditScope
    occurrence_start: datetime
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    timezone: str | None = None
    location: str | None = None
    participant_ids: list[UUID] | None = None
    recurrence_rule: RecurrenceRule | None = None


class EventOccurrenceDelete(BaseModel):
    scope: EditScope
    occurrence_start: datetime


class EventSeriesResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    organizer_id: UUID
    start_time: datetime
    end_time: datetime
    timezone: str
    location: str | None
    participant_ids: list[UUID]
    recurrence_rule: RecurrenceRule | None
    series_end_time: datetime | None
    parent_series_id: UUID | None
    is_cancelled: bool
    created_at: datetime
    updated_at: datetime


class EventOccurrenceResponse(BaseModel):
    series_id: UUID
    occurrence_id: str
    original_start: datetime
    start_time: datetime
    end_time: datetime
    title: str
    description: str | None
    organizer_id: UUID
    timezone: str
    location: str | None
    participant_ids: list[UUID]
    is_recurring: bool
    is_exception: bool
    is_cancelled: bool


class EventListResponse(BaseModel):
    items: list[EventOccurrenceResponse]
    total: int


# --- Invitations ---


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TENTATIVE = "tentative"


class InvitationCreate(BaseModel):
    event_series_id: UUID
    invitee_id: UUID
    invited_by: UUID
    occurrence_start: datetime | None = None


class InvitationStatusUpdate(BaseModel):
    status: InvitationStatus
    response_message: str | None = Field(default=None, max_length=500)


class InvitationResponse(BaseModel):
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
