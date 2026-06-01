import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EditScope(str, enum.Enum):
    SINGLE = "single"
    FUTURE = "future"
    ALL = "all"


class EventSeries(Base):
    """Master record for an event or recurring series."""

    __tablename__ = "event_series"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organizer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    participant_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recurrence_rule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    series_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_series.id"), nullable=True
    )
    is_cancelled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    overrides: Mapped[list["OccurrenceOverride"]] = relationship(back_populates="series")
    deleted_occurrences: Mapped[list["DeletedOccurrence"]] = relationship(back_populates="series")


class OccurrenceOverride(Base):
    """Per-occurrence modifications (edit single / exception instances)."""

    __tablename__ = "occurrence_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_series.id", ondelete="CASCADE"), index=True
    )
    original_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    participant_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    series: Mapped["EventSeries"] = relationship(back_populates="overrides")


class DeletedOccurrence(Base):
    """Cancelled single occurrences within a recurring series."""

    __tablename__ = "deleted_occurrences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_series.id", ondelete="CASCADE"), index=True
    )
    original_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    series: Mapped["EventSeries"] = relationship(back_populates="deleted_occurrences")
