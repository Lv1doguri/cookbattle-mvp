"""Login brute-force guard: too many failed attempts for one login id -> 429 for a while.

In-memory, so it resets on restart and isn't shared between processes. That's fine for one
uvicorn process; move it to Redis/DB before running several. Keyed by the login id (not IP) because
nicknames are public, which makes them easy targets; the trade-off is that someone can briefly lock
out a known nickname by failing on purpose.
"""
import datetime as dt
from collections import defaultdict, deque
from typing import Deque, Dict

from .. import clock
from ..errors import ApiError

MAX_FAILURES = 10
WINDOW = dt.timedelta(minutes=10)

_failures: Dict[str, Deque[dt.datetime]] = defaultdict(deque)


def _recent(key: str, now: dt.datetime) -> Deque[dt.datetime]:
    q = _failures[key]
    while q and now - q[0] > WINDOW:
        q.popleft()
    return q


def check(key: str) -> None:
    if len(_recent(key, clock.utcnow())) >= MAX_FAILURES:
        raise ApiError(429, "too_many_attempts", "로그인 시도가 너무 많아요. 잠시 후 다시 시도해주세요")


def record_failure(key: str) -> None:
    now = clock.utcnow()
    _recent(key, now).append(now)


def reset(key: str) -> None:
    _failures.pop(key, None)


def reset_all() -> None:
    _failures.clear()
