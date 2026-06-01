from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.clients import ServiceClients
from app.dependencies import DbSession, InternalAuth
from app.models import Invitation, InvitationStatus as DbInvitationStatus
from app.schemas import (
    InvitationCreate,
    InvitationListResponse,
    InvitationResponse,
    InvitationStatus,
    InvitationStatusUpdate,
)

router = APIRouter(prefix="/invitations", tags=["invitations"])
clients = ServiceClients()


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(payload: InvitationCreate, _auth: InternalAuth, db: DbSession) -> Invitation:
    await clients.validate_user(payload.invitee_id)
    await clients.validate_user(payload.invited_by)
    await clients.validate_event(payload.event_series_id)

    existing = await db.scalar(
        select(Invitation).where(
            Invitation.event_series_id == payload.event_series_id,
            Invitation.invitee_id == payload.invitee_id,
            Invitation.occurrence_start == payload.occurrence_start,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation already exists")

    invitation = Invitation(
        event_series_id=payload.event_series_id,
        invitee_id=payload.invitee_id,
        occurrence_start=payload.occurrence_start,
        invited_by=payload.invited_by,
        status=DbInvitationStatus.PENDING,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    _auth: InternalAuth,
    db: DbSession,
    invitee_id: UUID | None = None,
    event_series_id: UUID | None = None,
    status_filter: InvitationStatus | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> InvitationListResponse:
    query = select(Invitation)
    if invitee_id:
        query = query.where(Invitation.invitee_id == invitee_id)
    if event_series_id:
        query = query.where(Invitation.event_series_id == event_series_id)
    if status_filter:
        query = query.where(Invitation.status == DbInvitationStatus(status_filter.value))

    count_query = select(func.count()).select_from(Invitation)
    if invitee_id:
        count_query = count_query.where(Invitation.invitee_id == invitee_id)
    if event_series_id:
        count_query = count_query.where(Invitation.event_series_id == event_series_id)
    if status_filter:
        count_query = count_query.where(Invitation.status == DbInvitationStatus(status_filter.value))
    total = await db.scalar(count_query) or 0
    result = await db.execute(query.order_by(Invitation.created_at.desc()).offset(skip).limit(limit))
    items = result.scalars().all()
    return InvitationListResponse(items=items, total=total)


@router.get("/{invitation_id}", response_model=InvitationResponse)
async def get_invitation(invitation_id: UUID, _auth: InternalAuth, db: DbSession) -> Invitation:
    invitation = await db.get(Invitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    return invitation


@router.patch("/{invitation_id}/status", response_model=InvitationResponse)
async def update_invitation_status(
    invitation_id: UUID,
    payload: InvitationStatusUpdate,
    _auth: InternalAuth,
    db: DbSession,
) -> Invitation:
    invitation = await db.get(Invitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    invitation.status = DbInvitationStatus(payload.status.value)
    invitation.response_message = payload.response_message
    await db.commit()
    await db.refresh(invitation)
    return invitation


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invitation(invitation_id: UUID, _auth: InternalAuth, db: DbSession) -> None:
    invitation = await db.get(Invitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    await db.delete(invitation)
    await db.commit()
