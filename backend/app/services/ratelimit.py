"""아주 간단한 메모리 기반 요청 제한 (서버 1대 기준). 로그인 무차별 대입·유료 AI 호출 남용 방지."""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_lock = threading.Lock()
_hits = defaultdict(deque)


def hit(key: str, limit: int, window_seconds: int, message: str) -> None:
    """window 동안 limit회를 넘으면 429."""
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            retry = int(window_seconds - (now - q[0])) + 1
            raise HTTPException(status_code=429, detail=f"{message} ({retry}초 후 다시 시도해 주세요)",
                                headers={"Retry-After": str(retry)})
        q.append(now)


def reset(key: str) -> None:
    with _lock:
        _hits.pop(key, None)
