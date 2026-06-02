from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.config import settings
from app.http_client import service_request
from app.schemas import (
    EventCreate,
    EventListResponse,
    EventOccurrenceDelete,
    EventOccurrenceResponse,
    EventOccurrenceUpdate,
    EventSeriesResponse,
    EventUpdate,
)

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.post("", response_model=EventSeriesResponse, status_code=status.HTTP_201_CREATED, summary="Create event")
async def create_event(payload: EventCreate) -> EventSeriesResponse:
    response = await service_request(
        settings.event_service_url, "POST", "/events", json=payload.model_dump(mode="json")
    )
    event = EventSeriesResponse.model_validate(response.json())

    # Create series-level invitations for all participants on event creation.
    # Invitation endpoint already prevents duplicates per event+invitee.
    for participant_id in event.participant_ids:
        if participant_id == event.organizer_id:
            continue
        await service_request(
            settings.invitation_service_url,
            "POST",
            "/invitations",
            json={
                "event_series_id": str(event.id),
                "invitee_id": str(participant_id),
                "invited_by": str(event.organizer_id),
            },
        )

    return event


@router.get("", response_model=EventListResponse, summary="List event occurrences in date range")
async def list_events(
    range_start: datetime = Query(..., description="Inclusive start of date range"),
    range_end: datetime = Query(..., description="Exclusive end of date range"),
    user_id: UUID | None = Query(default=None, description="Filter by organizer or participant"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> EventListResponse:
    params = {
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "skip": skip,
        "limit": limit,
    }
    if user_id:
        params["user_id"] = str(user_id)
    response = await service_request(settings.event_service_url, "GET", "/events", params=params)
    return EventListResponse.model_validate(response.json())


@router.get("/{series_id}", response_model=EventSeriesResponse, summary="Get event series")
async def get_event(series_id: UUID) -> EventSeriesResponse:
    response = await service_request(settings.event_service_url, "GET", f"/events/{series_id}")
    return EventSeriesResponse.model_validate(response.json())


@router.patch("/{series_id}", response_model=EventSeriesResponse, summary="Update entire event series")
async def update_event(series_id: UUID, payload: EventUpdate) -> EventSeriesResponse:
    response = await service_request(
        settings.event_service_url,
        "PATCH",
        f"/events/{series_id}",
        json=payload.model_dump(mode="json", exclude_unset=True),
    )
    return EventSeriesResponse.model_validate(response.json())


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cancel event series")
async def delete_event(series_id: UUID) -> None:
    await service_request(settings.event_service_url, "DELETE", f"/events/{series_id}")


@router.get("/{series_id}/occurrences", response_model=EventListResponse, summary="List occurrences for series")
async def list_occurrences(
    series_id: UUID,
    range_start: datetime = Query(...),
    range_end: datetime = Query(...),
) -> EventListResponse:
    response = await service_request(
        settings.event_service_url,
        "GET",
        f"/events/{series_id}/occurrences",
        params={"range_start": range_start.isoformat(), "range_end": range_end.isoformat()},
    )
    return EventListResponse.model_validate(response.json())


@router.get(
    "/{series_id}/occurrences/detail",
    response_model=EventOccurrenceResponse,
    summary="Get single occurrence",
)
async def get_occurrence(
    series_id: UUID,
    occurrence_start: datetime = Query(...),
) -> EventOccurrenceResponse:
    response = await service_request(
        settings.event_service_url,
        "GET",
        f"/events/{series_id}/occurrences/detail",
        params={"occurrence_start": occurrence_start.isoformat()},
    )
    return EventOccurrenceResponse.model_validate(response.json())


@router.patch(
    "/{series_id}/occurrences",
    response_model=EventOccurrenceResponse | EventSeriesResponse,
    summary="Modify occurrence (single / future / all)",
)
async def update_occurrence(
    series_id: UUID, payload: EventOccurrenceUpdate
) -> EventOccurrenceResponse | EventSeriesResponse:
    response = await service_request(
        settings.event_service_url,
        "PATCH",
        f"/events/{series_id}/occurrences",
        json=payload.model_dump(mode="json"),
    )
    data = response.json()
    if "occurrence_id" in data:
        return EventOccurrenceResponse.model_validate(data)
    return EventSeriesResponse.model_validate(data)


@router.delete(
    "/{series_id}/occurrences",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/cancel occurrence (single / future / all)",
)
async def delete_occurrence(series_id: UUID, payload: EventOccurrenceDelete) -> None:
    await service_request(
        settings.event_service_url,
        "DELETE",
        f"/events/{series_id}/occurrences",
        json=payload.model_dump(mode="json"),
    )
