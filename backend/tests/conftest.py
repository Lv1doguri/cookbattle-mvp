import os
import tempfile

# Must be set before app modules are imported: they build the engine / mount uploads at import time.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="cookup-test-uploads-")

import datetime as dt  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import clock  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PASSWORD = "cookup123"


@pytest.fixture
def client():
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

    week 0 = the week that starts on the next Monday; weekday 0 = Monday. A battle created during
    week N ends at kst_at(N + 1, 0, 0).
    """
    today = clock.kst_date(dt.datetime.now(dt.timezone.utc))
    monday = today + dt.timedelta(days=7 - today.weekday()) + dt.timedelta(weeks=week)
    day = monday + dt.timedelta(days=weekday)
    return dt.datetime.combine(day, dt.time(hour), tzinfo=clock.KST).astimezone(dt.timezone.utc)


def signup(client, email, nickname=None, tier="intermediate"):
    r = client.post(
        "/auth/signup",
        json={"email": email, "nickname": nickname or "u_" + email.split("@")[0], "password": PASSWORD, "tier": tier},
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


def join(client, headers, battle_id, dish="치즈 스크램블 에그", description="우유를 조금 넣었어요"):
    return client.post(
        f"/battles/{battle_id}/entries",
        data={"dish_name": dish, "description": description},
        files={"photo": ("dish.png", PNG, "image/png")},
        headers=headers,
    )


def set_user(user_id, **values):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        for k, v in values.items():
            setattr(user, k, v)
        db.commit()
