import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TENTATIVE = "tentative"


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        UniqueConstraint(
            "event_series_id",
            "invitee_id",
            "occurrence_start",
            name="uq_invitation_per_occurrence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_series_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    invitee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    occurrence_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitation_status"), default=InvitationStatus.PENDING
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    response_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
