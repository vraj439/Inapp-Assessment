from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.user_client import UserServiceClient
from app.models import DeletedOccurrence, EventSeries, OccurrenceOverride
from app.recurrence import expand_occurrences, occurrence_id
from app.schemas import (
    EditScope,
    EventCreate,
    EventListResponse,
    EventOccurrenceDelete,
    EventOccurrenceResponse,
    EventOccurrenceUpdate,
    EventSeriesResponse,
    EventUpdate,
    RecurrenceRule,
)


def _uuid_list(raw: list) -> list[UUID]:
    return [UUID(str(item)) for item in raw]


class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_client = UserServiceClient()

    async def create_event(self, payload: EventCreate) -> EventSeriesResponse:
        if payload.end_time <= payload.start_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be after start_time")

        all_users = [payload.organizer_id, *payload.participant_ids]
        await self.user_client.validate_users_exist(all_users)

        series = EventSeries(
            title=payload.title,
            description=payload.description,
            organizer_id=payload.organizer_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            timezone=payload.timezone,
            location=payload.location,
            participant_ids=[str(uid) for uid in payload.participant_ids],
            recurrence_rule=payload.recurrence_rule.model_dump(mode="json") if payload.recurrence_rule else None,
        )
        self.db.add(series)
        await self.db.commit()
        await self.db.refresh(series)
        return self._to_series_response(series)

    async def get_series(self, series_id: UUID) -> EventSeriesResponse:
        series = await self._get_series_or_404(series_id)
        return self._to_series_response(series)

    async def update_series(self, series_id: UUID, payload: EventUpdate) -> EventSeriesResponse:
        series = await self._get_series_or_404(series_id)
        if series.is_cancelled:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Event series is cancelled")

        if payload.participant_ids is not None:
            await self.user_client.validate_users_exist(payload.participant_ids)

        if payload.title is not None:
            series.title = payload.title
        if payload.description is not None:
            series.description = payload.description
        if payload.start_time is not None:
            series.start_time = payload.start_time
        if payload.end_time is not None:
            series.end_time = payload.end_time
        if payload.timezone is not None:
            series.timezone = payload.timezone
        if payload.location is not None:
            series.location = payload.location
        if payload.participant_ids is not None:
            series.participant_ids = [str(uid) for uid in payload.participant_ids]
        if payload.recurrence_rule is not None:
            series.recurrence_rule = payload.recurrence_rule.model_dump(mode="json")

        if series.end_time <= series.start_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be after start_time")

        await self.db.commit()
        await self.db.refresh(series)
        return self._to_series_response(series)

    async def delete_series(self, series_id: UUID) -> None:
        series = await self._get_series_or_404(series_id)
        series.is_cancelled = True
        await self.db.commit()

    async def update_occurrence(
        self, series_id: UUID, payload: EventOccurrenceUpdate
    ) -> EventOccurrenceResponse | EventSeriesResponse:
        series = await self._get_series_or_404(series_id)
        if series.is_cancelled:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Event series is cancelled")

        if payload.scope == EditScope.SINGLE:
            return await self._edit_single_occurrence(series, payload)
        if payload.scope == EditScope.FUTURE:
            return await self._edit_future_occurrences(series, payload)
        if payload.scope == EditScope.ALL:
            return await self._edit_entire_series(series, payload)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid edit scope")

    async def delete_occurrence(self, series_id: UUID, payload: EventOccurrenceDelete) -> None:
        series = await self._get_series_or_404(series_id)
        if series.is_cancelled:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Event series is cancelled")

        if payload.scope == EditScope.SINGLE:
            await self._delete_single_occurrence(series, payload.occurrence_start)
        elif payload.scope == EditScope.FUTURE:
            series.series_end_time = payload.occurrence_start - timedelta(microseconds=1)
            await self.db.commit()
        elif payload.scope == EditScope.ALL:
            series.is_cancelled = True
            await self.db.commit()
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid edit scope")

    async def list_events(
        self,
        *,
        user_id: UUID | None = None,
        range_start: datetime,
        range_end: datetime,
        skip: int = 0,
        limit: int = 50,
    ) -> EventListResponse:
        if range_end <= range_start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="range_end must be after range_start")

        query = select(EventSeries).where(EventSeries.is_cancelled.is_(False))
        if user_id:
            query = query.where(
                (EventSeries.organizer_id == user_id)
                | EventSeries.participant_ids.contains([str(user_id)])
            )
        result = await self.db.execute(query)
        series_list = result.scalars().all()

        occurrences: list[EventOccurrenceResponse] = []
        for series in series_list:
            occurrences.extend(await self._expand_series_occurrences(series, range_start, range_end))

        occurrences.sort(key=lambda item: item.start_time)
        total = len(occurrences)
        page = occurrences[skip : skip + limit]
        return EventListResponse(items=page, total=total)

    async def get_occurrence(self, series_id: UUID, occurrence_start: datetime) -> EventOccurrenceResponse:
        series = await self._get_series_or_404(series_id)
        items = await self._expand_series_occurrences(
            series,
            occurrence_start - timedelta(days=1),
            occurrence_start + timedelta(days=1),
        )
        for item in items:
            if item.original_start == occurrence_start:
                return item
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")

    async def _edit_single_occurrence(
        self, series: EventSeries, payload: EventOccurrenceUpdate
    ) -> EventOccurrenceResponse:
        if payload.participant_ids is not None:
            await self.user_client.validate_users_exist(payload.participant_ids)

        existing = await self.db.scalar(
            select(OccurrenceOverride).where(
                OccurrenceOverride.series_id == series.id,
                OccurrenceOverride.original_start == payload.occurrence_start,
            )
        )
        if existing:
            override = existing
        else:
            override = OccurrenceOverride(series_id=series.id, original_start=payload.occurrence_start)
            self.db.add(override)

        if payload.title is not None:
            override.title = payload.title
        if payload.description is not None:
            override.description = payload.description
        if payload.start_time is not None:
            override.start_time = payload.start_time
        if payload.end_time is not None:
            override.end_time = payload.end_time
        if payload.timezone is not None:
            override.timezone = payload.timezone
        if payload.location is not None:
            override.location = payload.location
        if payload.participant_ids is not None:
            override.participant_ids = [str(uid) for uid in payload.participant_ids]

        await self.db.commit()
        expanded = await self._expand_series_occurrences(
            series,
            payload.occurrence_start - timedelta(seconds=1),
            payload.occurrence_start + timedelta(days=1),
        )
        if not expanded:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found in series")
        return expanded[0]

    async def _edit_future_occurrences(
        self, series: EventSeries, payload: EventOccurrenceUpdate
    ) -> EventSeriesResponse:
        series.series_end_time = payload.occurrence_start - timedelta(microseconds=1)

        new_start = payload.start_time or payload.occurrence_start
        duration = (payload.end_time or series.end_time) - (payload.start_time or series.start_time)
        if payload.end_time and payload.start_time:
            duration = payload.end_time - payload.start_time
        else:
            duration = series.end_time - series.start_time

        new_series = EventSeries(
            title=payload.title or series.title,
            description=payload.description if payload.description is not None else series.description,
            organizer_id=series.organizer_id,
            start_time=new_start,
            end_time=new_start + duration,
            timezone=payload.timezone or series.timezone,
            location=payload.location if payload.location is not None else series.location,
            participant_ids=(
                [str(uid) for uid in payload.participant_ids]
                if payload.participant_ids is not None
                else list(series.participant_ids)
            ),
            recurrence_rule=(
                payload.recurrence_rule.model_dump(mode="json")
                if payload.recurrence_rule
                else series.recurrence_rule
            ),
            parent_series_id=series.id,
        )
        self.db.add(new_series)
        await self.db.commit()
        await self.db.refresh(new_series)
        return self._to_series_response(new_series)

    async def _edit_entire_series(
        self, series: EventSeries, payload: EventOccurrenceUpdate
    ) -> EventSeriesResponse:
        update = EventUpdate(
            title=payload.title,
            description=payload.description,
            start_time=payload.start_time,
            end_time=payload.end_time,
            timezone=payload.timezone,
            location=payload.location,
            participant_ids=payload.participant_ids,
            recurrence_rule=payload.recurrence_rule,
        )
        return await self.update_series(series.id, update)

    async def _delete_single_occurrence(self, series: EventSeries, occurrence_start: datetime) -> None:
        existing = await self.db.scalar(
            select(DeletedOccurrence).where(
                DeletedOccurrence.series_id == series.id,
                DeletedOccurrence.original_start == occurrence_start,
            )
        )
        if not existing:
            self.db.add(DeletedOccurrence(series_id=series.id, original_start=occurrence_start))
            await self.db.commit()

    async def _expand_series_occurrences(
        self, series: EventSeries, range_start: datetime, range_end: datetime
    ) -> list[EventOccurrenceResponse]:
        recurrence = RecurrenceRule.model_validate(series.recurrence_rule) if series.recurrence_rule else None
        slots = expand_occurrences(
            series.start_time,
            series.end_time,
            recurrence,
            range_start,
            range_end,
            series.series_end_time,
        )

        overrides_result = await self.db.execute(
            select(OccurrenceOverride).where(OccurrenceOverride.series_id == series.id)
        )
        overrides = {row.original_start: row for row in overrides_result.scalars().all()}

        deleted_result = await self.db.execute(
            select(DeletedOccurrence).where(DeletedOccurrence.series_id == series.id)
        )
        deleted = {row.original_start for row in deleted_result.scalars().all()}

        items: list[EventOccurrenceResponse] = []
        for original_start, default_end in slots:
            if original_start in deleted:
                continue

            override = overrides.get(original_start)
            start_time = override.start_time if override and override.start_time else original_start
            end_time = override.end_time if override and override.end_time else default_end

            items.append(
                EventOccurrenceResponse(
                    series_id=series.id,
                    occurrence_id=occurrence_id(str(series.id), original_start),
                    original_start=original_start,
                    start_time=start_time,
                    end_time=end_time,
                    title=override.title if override and override.title else series.title,
                    description=override.description if override and override.description is not None else series.description,
                    organizer_id=series.organizer_id,
                    timezone=override.timezone if override and override.timezone else series.timezone,
                    location=override.location if override and override.location is not None else series.location,
                    participant_ids=_uuid_list(
                        override.participant_ids if override and override.participant_ids is not None else series.participant_ids
                    ),
                    is_recurring=series.recurrence_rule is not None,
                    is_exception=override is not None,
                    is_cancelled=False,
                )
            )
        return items

    async def _get_series_or_404(self, series_id: UUID) -> EventSeries:
        series = await self.db.get(EventSeries, series_id)
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return series

    def _to_series_response(self, series: EventSeries) -> EventSeriesResponse:
        recurrence = RecurrenceRule.model_validate(series.recurrence_rule) if series.recurrence_rule else None
        return EventSeriesResponse(
            id=series.id,
            title=series.title,
            description=series.description,
            organizer_id=series.organizer_id,
            start_time=series.start_time,
            end_time=series.end_time,
            timezone=series.timezone,
            location=series.location,
            participant_ids=_uuid_list(series.participant_ids),
            recurrence_rule=recurrence,
            series_end_time=series.series_end_time,
            parent_series_id=series.parent_series_id,
            is_cancelled=series.is_cancelled,
            created_at=series.created_at,
            updated_at=series.updated_at,
        )
