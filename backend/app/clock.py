"""All "what time is it" logic lives here so tests can patch clock.utcnow."""
import datetime as dt
from typing import Tuple
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def kst_date(now: dt.datetime) -> dt.date:
    return now.astimezone(KST).date()


def kst_day_bounds(day: dt.date) -> Tuple[dt.datetime, dt.datetime]:
    """[start, end) of a KST calendar day, as UTC-aware datetimes."""
    start = dt.datetime.combine(day, dt.time.min, tzinfo=KST)
    end = start + dt.timedelta(days=1)  # KST has no DST
    return start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)
