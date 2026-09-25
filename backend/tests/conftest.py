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
    with TestClient(app) as c:  # entering the context runs the lifespan: create tables + seed shop
        yield c


@pytest.fixture
def freeze(monkeypatch):
    def _freeze(when: dt.datetime):
        monkeypatch.setattr(clock, "utcnow", lambda: when)

    return _freeze


def kst_noon(days: int = 0) -> dt.datetime:
    """12:00 KST on (today + days), as UTC. Fixed mid-day so tests never straddle a KST midnight."""
    today = clock.kst_date(dt.datetime.now(dt.timezone.utc))
    day = today + dt.timedelta(days=days)
    return dt.datetime.combine(day, dt.time(12, 0), tzinfo=clock.KST).astimezone(dt.timezone.utc)


def signup(client, email, tier=None, nickname=None):
    body = {"email": email, "password": PASSWORD}
    if nickname:
        body["nickname"] = nickname
    r = client.post("/auth/signup", json=body)
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if tier:
        assert client.put("/me/tier", json={"tier": tier}, headers=headers).status_code == 200
    return headers, r.json()["user"]


def new_photo(client, headers):
    r = client.post("/photos", files={"file": ("shot.png", PNG, "image/png")}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["photo_id"]


def post_body(photo_id, **overrides):
    body = {
        "photo_id": photo_id,
        "caption": "오늘 처음으로 파스타를 만들어봤어요!",
        "title": "크림 파스타",
        "ingredients": [
            {"name": "파스타 면", "amount": "1인분"},
            {"name": "생크림", "amount": "200ml"},
            {"name": "마늘"},
        ],
        "steps": [{"text": "파스타를 8분 삶는다"}, {"text": "마늘을 볶고 생크림을 붓는다"}],
        "cost_krw": 4500,
        "cook_minutes": 20,
        "difficulty": "intermediate",
    }
    body.update(overrides)
    return body


def make_post(client, headers, **overrides):
    """Upload a fresh photo and publish a post with it. Returns the full PostCreatedOut."""
    r = client.post("/posts", json=post_body(new_photo(client, headers), **overrides), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def set_user(user_id, **values):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        for k, v in values.items():
            setattr(user, k, v)
        db.commit()
