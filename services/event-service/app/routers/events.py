from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import DbSession, InternalAuth
from app.schemas import (
    EventCreate,
    EventListResponse,
    EventOccurrenceDelete,
    EventOccurrenceResponse,
    EventOccurrenceUpdate,
    EventSeriesResponse,
    EventUpdate,
)
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventSeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, _auth: InternalAuth, db: DbSession) -> EventSeriesResponse:
    return await EventService(db).create_event(payload)


@router.get("", response_model=EventListResponse)
async def list_events(
    _auth: InternalAuth,
    db: DbSession,
    range_start: datetime = Query(..., description="Inclusive range start (ISO 8601)"),
    range_end: datetime = Query(..., description="Exclusive range end (ISO 8601)"),
    user_id: UUID | None = Query(default=None, description="Filter by organizer or participant"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> EventListResponse:
    return await EventService(db).list_events(
        user_id=user_id,
        range_start=range_start,
        range_end=range_end,
        skip=skip,
        limit=limit,
    )


@router.get("/{series_id}", response_model=EventSeriesResponse)
async def get_event(series_id: UUID, _auth: InternalAuth, db: DbSession) -> EventSeriesResponse:
    return await EventService(db).get_series(series_id)


@router.patch("/{series_id}", response_model=EventSeriesResponse)
async def update_event(
    series_id: UUID, payload: EventUpdate, _auth: InternalAuth, db: DbSession
) -> EventSeriesResponse:
    return await EventService(db).update_series(series_id, payload)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(series_id: UUID, _auth: InternalAuth, db: DbSession) -> None:
    await EventService(db).delete_series(series_id)


@router.get("/{series_id}/occurrences", response_model=EventListResponse)
async def list_occurrences(
    series_id: UUID,
    _auth: InternalAuth,
    db: DbSession,
    range_start: datetime = Query(...),
    range_end: datetime = Query(...),
) -> EventListResponse:
    service = EventService(db)
    model = await service._get_series_or_404(series_id)  # noqa: SLF001
    items = await service._expand_series_occurrences(model, range_start, range_end)  # noqa: SLF001
    return EventListResponse(items=items, total=len(items))


@router.get("/{series_id}/occurrences/detail", response_model=EventOccurrenceResponse)
async def get_occurrence(
    series_id: UUID,
    occurrence_start: datetime = Query(...),
    _auth: InternalAuth = None,
    db: DbSession = None,
) -> EventOccurrenceResponse:
    return await EventService(db).get_occurrence(series_id, occurrence_start)


@router.patch("/{series_id}/occurrences", response_model=EventOccurrenceResponse | EventSeriesResponse)
async def update_occurrence(
    series_id: UUID,
    payload: EventOccurrenceUpdate,
    _auth: InternalAuth,
    db: DbSession,
) -> EventOccurrenceResponse | EventSeriesResponse:
    return await EventService(db).update_occurrence(series_id, payload)


@router.delete("/{series_id}/occurrences", status_code=status.HTTP_204_NO_CONTENT)
async def delete_occurrence(
    series_id: UUID, payload: EventOccurrenceDelete, _auth: InternalAuth, db: DbSession
) -> None:
    await EventService(db).delete_occurrence(series_id, payload)
