import os
import tempfile

# Must be set before app modules are imported: they build the engine / mount uploads at import time.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="cookup-test-uploads-")

import datetime as dt  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import clock  # noqa: E402
from app.content import ENTRY_MIN_PHOTOS  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.services import throttle  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PASSWORD = "cookup123"


@pytest.fixture
def client():
    throttle.reset_all()
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # entering the context runs the lifespan: create tables + seed content
        yield c


@pytest.fixture
def freeze(monkeypatch):
    def _freeze(when: dt.datetime):
        monkeypatch.setattr(clock, "utcnow", lambda: when)

    return _freeze


def kst_at(week: int = 0, weekday: int = 0, hour: int = 12) -> dt.datetime:
    """A KST moment in the future, so login tokens minted while 'frozen' never look expired.

    week 0 = the week that starts on the next Monday; weekday 0 = Monday. Still used by theme-battle
    tests (THEME_COOKING_DAYS) and anywhere that just needs a stable future instant; daily-battle
    tests use `day_at` below instead, since daily battles run day-to-day rather than week-to-week.
    """
    today = clock.kst_date(dt.datetime.now(dt.timezone.utc))
    monday = today + dt.timedelta(days=7 - today.weekday()) + dt.timedelta(weeks=week)
    day = monday + dt.timedelta(days=weekday)
    return dt.datetime.combine(day, dt.time(hour), tzinfo=clock.KST).astimezone(dt.timezone.utc)


def day_at(day: int = 0, hour: int = 12) -> dt.datetime:
    """A KST moment in the future, so login tokens minted while 'frozen' never look expired.

    day 0 = tomorrow. A daily battle created on day N ends at day_at(N + 1, 0).
    """
    today = clock.kst_date(dt.datetime.now(dt.timezone.utc))
    target = today + dt.timedelta(days=1 + day)
    return dt.datetime.combine(target, dt.time(hour), tzinfo=clock.KST).astimezone(dt.timezone.utc)


def signup(client, email, nickname=None, tier="intermediate", username=None):
    r = client.post(
        "/auth/signup",
        json={
            "username": username or "id_" + email.split("@")[0],
            "email": email,
            "nickname": nickname or "u_" + email.split("@")[0],
            "password": PASSWORD,
            "tier": tier,
        },
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


def group(client, n, tier="intermediate", prefix="cook"):
    """n signed-up users in the same skill group: [(headers, user), ...]."""
    return [signup(client, f"{prefix}{i}@test.com", nickname=f"{prefix}{i}", tier=tier) for i in range(n)]


def current_battle(client, headers, tier=None):
    r = client.get("/battles/current", params={"tier": tier} if tier else None, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def camera_photo(client, headers):
    """What the camera screen does right after the shot: upload it, get photo_id back."""
    r = client.post("/photos", files={"file": ("shot.png", PNG, "image/png")}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def join(client, headers, battle_id, dish="치즈 스크램블 에그", description="우유를 조금 넣었어요", photo_id=None, photo_ids=None):
    """Submit an entry with ENTRY_MIN_PHOTOS angle photos. `photo_id` is a shorthand for tests
    that only care about one specific (first) photo; the rest are auto-filled with fresh ones
    so the minimum is met. Pass `photo_ids` directly to control the whole list."""
    if photo_ids is None:
        photo_ids = [photo_id if photo_id is not None else camera_photo(client, headers)["photo_id"]]
        while len(photo_ids) < ENTRY_MIN_PHOTOS:
            photo_ids.append(camera_photo(client, headers)["photo_id"])
    return client.post(
        f"/battles/{battle_id}/entries",
        json={"photo_ids": photo_ids, "dish_name": dish, "description": description},
        headers=headers,
    )


def set_user(user_id, **values):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        for k, v in values.items():
            setattr(user, k, v)
        db.commit()
