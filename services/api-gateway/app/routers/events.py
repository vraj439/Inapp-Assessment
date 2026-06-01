from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Query, status

from app.config import settings
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

HEADERS = {"X-Internal-Api-Key": settings.internal_api_key}
BASE = settings.event_service_url.rstrip("/")


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await client.request(method, f"{BASE}{path}", headers=HEADERS, **kwargs)


@router.post("", response_model=EventSeriesResponse, status_code=status.HTTP_201_CREATED, summary="Create event")
async def create_event(payload: EventCreate) -> EventSeriesResponse:
    response = await _request("POST", "/events", json=payload.model_dump(mode="json"))
    response.raise_for_status()
    return EventSeriesResponse.model_validate(response.json())


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
    response = await _request("GET", "/events", params=params)
    response.raise_for_status()
    return EventListResponse.model_validate(response.json())


@router.get("/{series_id}", response_model=EventSeriesResponse, summary="Get event series")
async def get_event(series_id: UUID) -> EventSeriesResponse:
    response = await _request("GET", f"/events/{series_id}")
    response.raise_for_status()
    return EventSeriesResponse.model_validate(response.json())


@router.patch("/{series_id}", response_model=EventSeriesResponse, summary="Update entire event series")
async def update_event(series_id: UUID, payload: EventUpdate) -> EventSeriesResponse:
    response = await _request(
        "PATCH", f"/events/{series_id}", json=payload.model_dump(mode="json", exclude_unset=True)
    )
    response.raise_for_status()
    return EventSeriesResponse.model_validate(response.json())


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cancel event series")
async def delete_event(series_id: UUID) -> None:
    response = await _request("DELETE", f"/events/{series_id}")
    response.raise_for_status()


@router.get("/{series_id}/occurrences", response_model=EventListResponse, summary="List occurrences for series")
async def list_occurrences(
    series_id: UUID,
    range_start: datetime = Query(...),
    range_end: datetime = Query(...),
) -> EventListResponse:
    response = await _request(
        "GET",
        f"/events/{series_id}/occurrences",
        params={"range_start": range_start.isoformat(), "range_end": range_end.isoformat()},
    )
    response.raise_for_status()
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
    response = await _request(
        "GET",
        f"/events/{series_id}/occurrences/detail",
        params={"occurrence_start": occurrence_start.isoformat()},
    )
    response.raise_for_status()
    return EventOccurrenceResponse.model_validate(response.json())


@router.patch(
    "/{series_id}/occurrences",
    response_model=EventOccurrenceResponse | EventSeriesResponse,
    summary="Modify occurrence (single / future / all)",
)
async def update_occurrence(
    series_id: UUID, payload: EventOccurrenceUpdate
) -> EventOccurrenceResponse | EventSeriesResponse:
    response = await _request("PATCH", f"/events/{series_id}/occurrences", json=payload.model_dump(mode="json"))
    response.raise_for_status()
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
    response = await _request(
        "DELETE", f"/events/{series_id}/occurrences", json=payload.model_dump(mode="json")
    )
    response.raise_for_status()
