"""Expand recurring events into occurrences using python-dateutil rrule."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil import rrule
from dateutil.rrule import DAILY, FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, YEARLY

from app.schemas import RecurrenceFrequency, RecurrenceRule, Weekday

WEEKDAY_MAP = {
    Weekday.MO: MO,
    Weekday.TU: TU,
    Weekday.WE: WE,
    Weekday.TH: TH,
    Weekday.FR: FR,
    Weekday.SA: SA,
    Weekday.SU: SU,
}

FREQ_MAP = {
    RecurrenceFrequency.DAILY: DAILY,
    RecurrenceFrequency.WEEKLY: WEEKLY,
    RecurrenceFrequency.MONTHLY: MONTHLY,
    RecurrenceFrequency.YEARLY: YEARLY,
}


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC"))


def build_rrule(series_start: datetime, rule: RecurrenceRule) -> rrule.rrule:
    dtstart = _to_utc(series_start).replace(tzinfo=None)
    kwargs: dict = {
        "freq": FREQ_MAP[rule.frequency],
        "interval": rule.interval,
        "dtstart": dtstart,
    }
    if rule.by_weekday:
        kwargs["byweekday"] = [WEEKDAY_MAP[day] for day in rule.by_weekday]
    if rule.by_monthday:
        kwargs["bymonthday"] = rule.by_monthday
    if rule.until:
        kwargs["until"] = _to_utc(rule.until).replace(tzinfo=None)
    if rule.count:
        kwargs["count"] = rule.count
    return rrule.rrule(**kwargs)


def expand_occurrences(
    series_start: datetime,
    series_end: datetime,
    recurrence_rule: RecurrenceRule | None,
    range_start: datetime,
    range_end: datetime,
    series_end_time: datetime | None = None,
    max_occurrences: int = 500,
) -> list[tuple[datetime, datetime]]:
    duration = series_end - series_start
    range_start_utc = _to_utc(range_start)
    range_end_utc = _to_utc(range_end)

    if recurrence_rule is None:
        if series_start <= range_end_utc and series_end >= range_start_utc:
            return [(series_start, series_end)]
        return []

    rule = build_rrule(series_start, recurrence_rule)
    effective_until = range_end_utc.replace(tzinfo=None)
    if series_end_time:
        effective_until = min(effective_until, _to_utc(series_end_time).replace(tzinfo=None))

    starts: list[datetime] = []
    for occurrence_start in rule:
        if occurrence_start > effective_until:
            break
        occurrence_start = occurrence_start.replace(tzinfo=ZoneInfo("UTC"))
        occurrence_end = occurrence_start + duration
        if occurrence_end < range_start_utc:
            continue
        if occurrence_start > range_end_utc:
            break
        starts.append(occurrence_start)
        if len(starts) >= max_occurrences:
            break

    return [(start, start + duration) for start in starts]


def occurrence_id(series_id: str, original_start: datetime) -> str:
    return f"{series_id}:{_to_utc(original_start).isoformat()}"
