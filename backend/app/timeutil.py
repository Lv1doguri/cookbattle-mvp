import datetime as dt
from zoneinfo import ZoneInfo

from .config import settings


def _tz():
    return ZoneInfo(settings.timezone)


def today() -> dt.date:
    """서비스 기준 시간대(기본 한국)의 오늘 날짜."""
    return dt.datetime.now(_tz()).date()


def utcnow() -> dt.datetime:
    """DB 저장용 UTC 시각 (naive)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def to_local_str(value: dt.datetime) -> str:
    """UTC naive 시각 → 서비스 시간대 표시 문자열 (예: '2026-09-25 14:03')."""
    if value is None:
        return ""
    return value.replace(tzinfo=dt.timezone.utc).astimezone(_tz()).strftime("%Y-%m-%d %H:%M")


def month_start_utc() -> dt.datetime:
    """이번 달 1일 0시(서비스 시간대)를 UTC naive로. '이번 달' 통계용."""
    now = dt.datetime.now(_tz())
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(dt.timezone.utc).replace(tzinfo=None)
