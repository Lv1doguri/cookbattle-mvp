"""All "what time is it" logic lives here so tests can patch clock.utcnow."""
import datetime as dt
from typing import Tuple
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def kst_date(now: dt.datetime) -> dt.date:
    return now.astimezone(KST).date()


def kst_week_start(day: dt.date) -> dt.date:
    """The Monday of the week containing `day`."""
    return day - dt.timedelta(days=day.weekday())


def kst_month_bounds(day: dt.date) -> Tuple[dt.datetime, dt.datetime]:
    """[start, end) of the KST calendar month containing `day`, as UTC-aware datetimes."""
    first = day.replace(day=1)
    next_first = (first + dt.timedelta(days=32)).replace(day=1)
    return kst_day_bounds(first)[0], kst_day_bounds(next_first)[0]


def kst_day_bounds(day: dt.date) -> Tuple[dt.datetime, dt.datetime]:
    """[start, end) of a KST calendar day, as UTC-aware datetimes."""
    start = dt.datetime.combine(day, dt.time.min, tzinfo=KST)
    end = start + dt.timedelta(days=1)  # KST has no DST
    return start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)
