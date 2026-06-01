from uuid import UUID

from fastapi import APIRouter, Query, status

from app.config import settings
from app.http_client import service_request
from app.schemas import (
    InvitationCreate,
    InvitationListResponse,
    InvitationResponse,
    InvitationStatus,
    InvitationStatusUpdate,
)

router = APIRouter(prefix="/api/v1/invitations", tags=["Invitations"])


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED, summary="Send invitation")
async def create_invitation(payload: InvitationCreate) -> InvitationResponse:
    response = await service_request(
        settings.invitation_service_url, "POST", "/invitations", json=payload.model_dump(mode="json")
    )
    return InvitationResponse.model_validate(response.json())


@router.get("", response_model=InvitationListResponse, summary="List invitations")
async def list_invitations(
    invitee_id: UUID | None = None,
    event_series_id: UUID | None = None,
    status_filter: InvitationStatus | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> InvitationListResponse:
    params: dict = {"skip": skip, "limit": limit}
    if invitee_id:
        params["invitee_id"] = str(invitee_id)
    if event_series_id:
        params["event_series_id"] = str(event_series_id)
    if status_filter:
        params["status"] = status_filter.value
    response = await service_request(settings.invitation_service_url, "GET", "/invitations", params=params)
    return InvitationListResponse.model_validate(response.json())


@router.get("/{invitation_id}", response_model=InvitationResponse, summary="Get invitation")
async def get_invitation(invitation_id: UUID) -> InvitationResponse:
    response = await service_request(settings.invitation_service_url, "GET", f"/invitations/{invitation_id}")
    return InvitationResponse.model_validate(response.json())


@router.patch(
    "/{invitation_id}/status",
    response_model=InvitationResponse,
    summary="Respond to invitation (accept / reject / tentative)",
)
async def respond_to_invitation(
    invitation_id: UUID, payload: InvitationStatusUpdate
) -> InvitationResponse:
    response = await service_request(
        settings.invitation_service_url,
        "PATCH",
        f"/invitations/{invitation_id}/status",
        json=payload.model_dump(mode="json"),
    )
    return InvitationResponse.model_validate(response.json())


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke invitation")
async def delete_invitation(invitation_id: UUID) -> None:
    await service_request(settings.invitation_service_url, "DELETE", f"/invitations/{invitation_id}")
