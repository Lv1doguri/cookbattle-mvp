import datetime as dt

from app.database import SessionLocal
from app.enums import Tier
from app.models import Exchange, LedgerEntry, User
from app.services.battles import get_or_create_daily_battle, get_or_create_theme_battle, week_label
from app.services.points import level_for
from sqlalchemy import func, select

from .conftest import PASSWORD, PNG, camera_photo, current_battle, distinct_photo, group, join, kst_at, set_user, signup


def _iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def run_battle(client, freeze, votes_for=(2, 2, 1, 0)):
    """One battle in the 중급 group, cooked and voted on, left frozen 1 hour into its 24-hour
    voting window. votes_for[i] = votes cook_i receives. cook0 submits first, cook1 second, ...
    Voters are separate non-participants.

    Callers should `freeze(kst_at(1, 1, 1))` afterwards (past the voting window) before checking
    `/battles/{id}/result`.
    Returns (cooks, voters, battle_id, entry_ids).
    """
    freeze(kst_at(0, 2, 12))
    cooks = group(client, len(votes_for), prefix="cook")
    voters = group(client, sum(votes_for), prefix="voter")
    battle_id = current_battle(client, cooks[0][0])["id"]
    entry_ids = []
    for i, (headers, _) in enumerate(cooks):
        freeze(kst_at(0, 2, 12) + dt.timedelta(minutes=i))
        r = join(client, headers, battle_id, dish=f"요리{i}")
        assert r.status_code == 201, r.text
        entry_ids.append(r.json()["entry"]["id"])
    freeze(kst_at(1, 0, 1))  # cooking ended (kst_at(1, 0, 0)); now 1h into the voting window
    v = iter(voters)
    for entry_id, n in zip(entry_ids, votes_for):
        for _ in range(n):
            assert client.post(f"/entries/{entry_id}/vote", headers=next(v)[0]).status_code == 200
    return cooks, voters, battle_id, entry_ids


# ------------------------------------------------------------------ auth
def test_signup_login_and_me(client):
    r = client.post(
        "/auth/signup",
        json={"email": "Yuri@Test.com", "nickname": "Yuri", "password": PASSWORD, "tier": "intermediate"},
    )
    assert r.status_code == 201
    me = r.json()["user"]
    assert (me["email"], me["nickname"], me["tier"], me["tier_label"]) == ("yuri@test.com", "Yuri", "intermediate", "중급")
    assert me["progress"] == {
        "level": 1, "points": 30, "total_points": 30, "level_start_points": 0, "next_level_points": 100,
        "points_to_next_level": 70,
    }  # 가입 보너스 +30P
    assert me["pending_tier"] is None and me["saved_recipe_count"] == 0 and me["review_count"] == 0

    same_nick = client.post(
        "/auth/signup", json={"email": "b@test.com", "nickname": "YURI", "password": PASSWORD, "tier": "beginner"}
    )
    assert same_nick.status_code == 409 and same_nick.json()["code"] == "nickname_taken"
    assert same_nick.json()["detail"] == "이미 사용 중인 닉네임입니다"
    same_email = client.post(
        "/auth/signup", json={"email": "YURI@test.com", "nickname": "Other", "password": PASSWORD, "tier": "beginner"}
    )
    assert same_email.status_code == 409 and same_email.json()["code"] == "email_taken"

    wrong = client.post("/auth/login", json={"email": "yuri@test.com", "password": "wrong-password"})
    assert wrong.status_code == 401 and wrong.json()["code"] == "invalid_credentials"
    unknown = client.post("/auth/login", json={"email": "nobody@test.com", "password": PASSWORD})
    assert unknown.status_code == 401 and unknown.json()["detail"] == wrong.json()["detail"]

    ok = client.post("/auth/login", json={"email": "YURI@test.com", "password": PASSWORD})
    assert ok.status_code == 200
    headers = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert client.get("/me", headers=headers).json()["id"] == me["id"]
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_nickname_availability_and_validation(client):
    signup(client, "a@test.com", nickname="자취생")
    assert client.get("/auth/nickname-available", params={"nickname": "자취생"}).json() == {"available": False}
    assert client.get("/auth/nickname-available", params={"nickname": "새닉네임"}).json() == {"available": True}
    assert client.get("/auth/nickname-available", params={"nickname": "a"}).status_code == 422

    bad = client.post("/auth/signup", json={"email": "x@test.com", "nickname": "닉", "password": "short", "tier": "beginner"})
    assert bad.status_code == 422 and isinstance(bad.json()["detail"], str) and bad.json()["code"] == "validation_error"
    no_tier = client.post("/auth/signup", json={"email": "x@test.com", "nickname": "닉네임", "password": PASSWORD})
    assert no_tier.status_code == 422
    bad_tier = client.post(
        "/auth/signup", json={"email": "x@test.com", "nickname": "닉네임", "password": PASSWORD, "tier": "expert"}
    )
    assert bad_tier.status_code == 422
    assert client.get("/nope").json()["detail"] == "Not Found"


def test_level_thresholds():
    assert [level_for(p) for p in (0, 99, 100, 299, 300, 699, 700, 1499, 1500, 2299, 2300)] == \
        [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6]


def test_progress_matches_the_home_mockup(client):
    _, me = signup(client, "a@test.com", tier="intermediate")
    set_user(me["id"], points=150, total_points=150)
    headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'email': 'a@test.com', 'password': PASSWORD}).json()['access_token']}"}
    progress = client.get("/me", headers=headers).json()["progress"]
    assert progress["level"] == 2 and progress["next_level_points"] == 300 and progress["points_to_next_level"] == 150


# ------------------------------------------------------------------ profile
def test_profile_edit(client):
    a, _ = signup(client, "a@test.com", nickname="Yuri", tier="beginner")
    signup(client, "b@test.com", nickname="Minsu")

    taken = client.patch("/me", json={"nickname": "MINSU"}, headers=a)
    assert taken.status_code == 409 and taken.json()["code"] == "nickname_taken"
    assert client.patch("/me", json={"nickname": "yuri"}, headers=a).status_code == 200  # own nickname, new case
    dup_email = client.patch("/me", json={"email": "B@test.com"}, headers=a)
    assert dup_email.status_code == 409 and dup_email.json()["code"] == "email_taken"

    changed = client.patch("/me", json={"nickname": "새이름", "email": "new@test.com", "password": "newpass123"}, headers=a)
    assert changed.status_code == 200 and changed.json()["nickname"] == "새이름" and changed.json()["email"] == "new@test.com"
    assert client.post("/auth/login", json={"email": "new@test.com", "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"email": "new@test.com", "password": "newpass123"}).status_code == 200
    assert client.patch("/me", json={"password": "short"}, headers=a).status_code == 422
    assert client.patch("/me", json={}, headers=a).status_code == 200  # nothing sent, nothing changes


def test_tier_change_applies_from_the_next_battle(client, freeze):
    freeze(kst_at(0, 2, 12))
    a, me = signup(client, "a@test.com", tier="beginner")

    pending = client.patch("/me", json={"tier": "intermediate"}, headers=a).json()
    assert pending["tier"] == "beginner" and pending["pending_tier"] == "intermediate"
    assert pending["pending_tier_label"] == "중급" and _iso(pending["pending_tier_applies_at"]) == kst_at(1, 0, 0)
    assert current_battle(client, a)["tier"] == "beginner"  # this week's group is unchanged

    same = client.patch("/me", json={"tier": "beginner"}, headers=a).json()
    assert same["pending_tier"] is None  # changing back cancels the switch
    client.patch("/me", json={"tier": "advanced"}, headers=a)

    freeze(kst_at(1, 0, 1))
    switched = client.get("/me", headers=a).json()
    assert switched["tier"] == "advanced" and switched["pending_tier"] is None
    assert current_battle(client, a)["tier"] == "advanced"


def test_avatar_upload(client):
    a, _ = signup(client, "a@test.com")
    bad = client.put("/me/avatar", files={"file": ("x.png", b"not an image", "image/png")}, headers=a)
    assert bad.status_code == 400 and bad.json()["code"] == "unsupported_image"
    assert client.put("/me/avatar", files={"file": ("x.png", PNG, "image/png")}).status_code == 401

    first = client.put("/me/avatar", files={"file": ("x.png", PNG, "image/png")}, headers=a).json()["avatar_url"]
    assert first.startswith("/uploads/") and client.get(first).status_code == 200
    second = client.put("/me/avatar", files={"file": ("y.png", PNG, "image/png")}, headers=a).json()["avatar_url"]
    assert second != first and client.get(second).status_code == 200 and client.get(first).status_code == 404


def test_signup_without_email_then_login_by_nickname(client):
    """The signup screen has no email field, so email is optional and the nickname doubles as the login id."""
    r = client.post("/auth/signup", json={"nickname": "자취생", "password": PASSWORD, "tier": "beginner"})
    assert r.status_code == 201 and r.json()["user"]["email"] is None
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post("/auth/signup", json={"nickname": "또다른", "password": PASSWORD, "tier": "beginner"}).status_code == 201

    assert client.post("/auth/login", json={"email": "자취생", "password": PASSWORD}).status_code == 200
    assert client.post("/auth/login", json={"email": "  자취생 ", "password": PASSWORD}).status_code == 200
    assert client.post("/auth/login", json={"email": "자취생", "password": "wrong-password"}).status_code == 401
    assert client.post("/auth/login", json={"email": "없는사람", "password": PASSWORD}).status_code == 401

    added = client.patch("/me", json={"email": "You@University.ac.kr"}, headers=headers).json()
    assert added["email"] == "you@university.ac.kr"
    assert client.post("/auth/login", json={"email": "YOU@university.ac.kr", "password": PASSWORD}).status_code == 200
    dup = client.post(
        "/auth/signup", json={"email": "you@university.ac.kr", "nickname": "복사본", "password": PASSWORD, "tier": "beginner"}
    )
    assert dup.status_code == 409 and dup.json()["code"] == "email_taken"
    bad_email = client.post(
        "/auth/signup", json={"email": "not-an-email", "nickname": "복사본", "password": PASSWORD, "tier": "beginner"}
    )
    assert bad_email.status_code == 422


def test_login_is_throttled_after_repeated_failures(client, freeze):
    signup(client, "a@test.com", nickname="Yuri")
    wrong = {"email": "yuri", "password": "wrong-password"}
    for _ in range(10):
        assert client.post("/auth/login", json=wrong).status_code == 401
    blocked = client.post("/auth/login", json={"email": "Yuri", "password": PASSWORD})  # even the right password
    assert blocked.status_code == 429 and blocked.json()["code"] == "too_many_attempts"
    assert client.post("/auth/login", json={"email": "someone-else", "password": PASSWORD}).status_code == 401  # not blocked

    freeze(kst_at(0, 2, 12))  # the 10-minute window has long passed
    assert client.post("/auth/login", json={"email": "Yuri", "password": PASSWORD}).status_code == 200


def test_successful_login_clears_the_failure_count(client):
    signup(client, "a@test.com", nickname="Yuri")
    for _ in range(9):
        client.post("/auth/login", json={"email": "Yuri", "password": "wrong-password"})
    assert client.post("/auth/login", json={"email": "Yuri", "password": PASSWORD}).status_code == 200
    for _ in range(9):
        assert client.post("/auth/login", json={"email": "Yuri", "password": "wrong-password"}).status_code == 401
    assert client.post("/auth/login", json={"email": "Yuri", "password": PASSWORD}).status_code == 200


# ------------------------------------------------------------------ camera photos
def test_camera_photo_rules(client, freeze):
    freeze(kst_at(0, 2, 12))
    a, _ = signup(client, "a@test.com", tier="intermediate")
    b, _ = signup(client, "b@test.com", tier="intermediate")
    assert client.post("/photos", files={"file": ("x.png", PNG, "image/png")}).status_code == 401
    bad = client.post("/photos", files={"file": ("x.png", b"not an image", "image/png")}, headers=a)
    assert bad.status_code == 400 and bad.json()["code"] == "unsupported_image"
    too_big = client.post("/photos", files={"file": ("x.png", PNG + b"0" * (8 * 1024 * 1024), "image/png")}, headers=a)
    assert too_big.status_code == 413 and too_big.json()["code"] == "file_too_large"

    shot = camera_photo(client, a)
    assert shot["photo_url"].startswith("/uploads/") and client.get(shot["photo_url"]).status_code == 200
    assert _iso(shot["captured_at"]) == kst_at(0, 2, 12) and _iso(shot["expires_at"]) == kst_at(0, 2, 13)

    battle_id = current_battle(client, a)["id"]
    stolen = join(client, b, battle_id, photo_id=shot["photo_id"])  # someone else's photo
    assert stolen.status_code == 404 and stolen.json()["code"] == "photo_not_found"
    ok = join(client, a, battle_id, photo_id=shot["photo_id"])
    assert ok.status_code == 201 and ok.json()["entry"]["photo_url"] == shot["photo_url"]

    freeze(kst_at(1, 1, 12))  # next week's battle: the used photo can't be recycled
    next_battle = current_battle(client, a)["id"]
    reuse = join(client, a, next_battle, photo_id=shot["photo_id"])
    assert reuse.status_code == 409 and reuse.json()["code"] == "photo_already_used"

    stale = camera_photo(client, a)
    freeze(kst_at(1, 1, 14))  # two hours later: too old to submit
    expired = join(client, a, next_battle, photo_id=stale["photo_id"])
    assert expired.status_code == 400 and expired.json()["code"] == "photo_expired"

    camera_photo(client, a)  # the next upload sweeps this user's expired, unused photos
    assert client.get(stale["photo_url"]).status_code == 404
    assert client.get(shot["photo_url"]).status_code == 200  # the one backing an entry stays


def test_camera_upload_rate_limit(client):
    a, _ = signup(client, "a@test.com")
    for _ in range(30):
        camera_photo(client, a)
    limited = client.post("/photos", files={"file": ("x.png", PNG, "image/png")}, headers=a)
    assert limited.status_code == 429 and limited.json()["code"] == "too_many_uploads"


# ------------------------------------------------------------------ battles: setup
def test_weekly_battle_schedule(client):
    with SessionLocal() as db:
        battle = get_or_create_daily_battle(db, Tier.intermediate, dt.datetime(2026, 9, 23, 3, 0, tzinfo=dt.timezone.utc))
        assert battle.theme == "계란 요리" and battle.description == "계란이 메인인 든든한 한 끼"
        assert battle.starts_at == dt.datetime(2026, 9, 20, 15, 0, tzinfo=dt.timezone.utc)  # Mon 9/21 00:00 KST
        assert battle.ends_at == dt.datetime(2026, 9, 27, 15, 0, tzinfo=dt.timezone.utc)  # Mon 9/28 00:00 KST
        assert battle.voting_ends_at == dt.datetime(2026, 9, 28, 15, 0, tzinfo=dt.timezone.utc)  # + 24h
        beginner = get_or_create_daily_battle(db, Tier.beginner, dt.datetime(2026, 9, 23, 3, 0, tzinfo=dt.timezone.utc))
        assert beginner.id != battle.id and beginner.description == "간단한 계란 요리면 OK"
        assert get_or_create_daily_battle(db, Tier.intermediate, dt.datetime(2026, 9, 25, 3, 0, tzinfo=dt.timezone.utc)).id == battle.id
    assert week_label(dt.date(2026, 9, 21)) == "9월 4주차"
    assert week_label(dt.date(2026, 8, 31)) == "9월 1주차"  # its Thursday is Sep 3


def test_theme_battle_is_shared_across_tiers(client):
    with SessionLocal() as db:
        now = dt.datetime(2026, 9, 1, 3, 0, tzinfo=dt.timezone.utc)  # Tue 9/1 12:00 KST
        theme = get_or_create_theme_battle(db, now)
        assert theme.tier is None and theme.kind.value == "theme"
        # same 3-day cooking cycle regardless of who's asking, and it's the same row every time
        assert get_or_create_theme_battle(db, now + dt.timedelta(hours=1)).id == theme.id
        assert theme.voting_ends_at == theme.ends_at + dt.timedelta(hours=24)

    a, _ = signup(client, "a@test.com", tier="beginner")
    b, _ = signup(client, "b@test.com", tier="advanced")
    theme_a = client.get("/battles/current", params={"kind": "theme"}, headers=a).json()
    theme_b = client.get("/battles/current", params={"kind": "theme"}, headers=b).json()
    assert theme_a["id"] == theme_b["id"] and theme_a["tier"] is None and theme_a["tier_label"] is None
    assert theme_a["is_my_group"] and theme_b["is_my_group"]  # everyone's group, regardless of tier


def test_current_battle_and_joining(client, freeze):
    freeze(kst_at(0, 2, 12))
    beginner, _ = signup(client, "a@test.com", tier="beginner")
    inter, inter_user = signup(client, "b@test.com", tier="intermediate")
    assert client.get("/battles/current").status_code == 401

    view = current_battle(client, inter)
    assert view["tier"] == "intermediate" and view["title"] == f"{view['theme']} 대결"
    assert view["is_open"] and view["is_my_group"] and view["can_join"] and not view["has_joined"]
    assert view["participants"] == 0 and view["my_entry"] is None and view["last_result"] is None
    assert view["days_left"] == 5 and view["seconds_left"] == 4.5 * 86400 // 1  # Wed 12:00 -> Mon 00:00 KST
    other_tab = current_battle(client, inter, tier="beginner")
    assert other_tab["is_my_group"] is False and other_tab["can_join"] is False
    assert current_battle(client, beginner)["tier"] == "beginner"  # default = my own group

    wrong = join(client, beginner, view["id"])
    assert wrong.status_code == 403 and wrong.json()["code"] == "wrong_group" and "초급" in wrong.json()["detail"]

    no_photo = client.post(f"/battles/{view['id']}/entries", json={"dish_name": "요리"}, headers=inter)
    assert no_photo.status_code == 422
    unknown_photo = join(client, inter, view["id"], photo_id=999)
    assert unknown_photo.status_code == 404 and unknown_photo.json()["code"] == "photo_not_found"
    blank = join(client, inter, view["id"], dish="   ")
    assert blank.status_code == 422
    assert client.get("/me", headers=inter).json()["progress"]["points"] == 30  # only the signup bonus so far

    joined = join(client, inter, view["id"], dish="치즈 스크램블 에그", description="치즈는 마지막에!")
    assert joined.status_code == 201
    body = joined.json()
    assert (body["points_awarded"], body["points"]) == (40, 70)  # 참가 10P + 첫 대결 보너스 30P
    assert body["entry"]["dish_name"] == "치즈 스크램블 에그" and body["entry"]["state"] == "mine"
    assert body["entry"]["author"]["nickname"] == "u_b" and client.get(body["entry"]["photo_url"]).status_code == 200

    again = join(client, inter, view["id"])
    assert again.status_code == 409 and again.json()["code"] == "already_entered"
    after = current_battle(client, inter)
    assert after["can_join"] is False and after["has_joined"] and after["participants"] == 1
    assert after["my_entry"]["id"] == body["entry"]["id"]
    assert client.get("/me", headers=inter).json()["progress"]["points"] == 70

    freeze(kst_at(1, 0, 1))  # the week is over
    late, _ = signup(client, "c@test.com", tier="intermediate")
    closed = join(client, late, view["id"])
    assert closed.status_code == 400 and closed.json()["code"] == "battle_closed"


# ------------------------------------------------------------------ battles: voting
def test_voting_only_opens_after_cooking_ends(client, freeze):
    """투표는 대회 종료 후 24시간 동안만 가능해요. 요리 기간에는 아무도 투표할 수 없어요."""
    freeze(kst_at(0, 2, 12))
    (c0, _), (c1, _), (c2, _) = group(client, 3, prefix="cook")
    voter, _ = signup(client, "voter@test.com", nickname="voter", tier="intermediate")
    outsider, _ = signup(client, "out@test.com", nickname="outsider", tier="beginner")
    battle_id = current_battle(client, c0)["id"]
    entry_ids = [join(client, h, battle_id, dish=f"요리{i}").json()["entry"]["id"] for i, h in enumerate((c0, c1, c2))]

    cooking = client.get(f"/battles/{battle_id}/entries", headers=voter).json()
    assert cooking["phase"] == "cooking" and not cooking["can_vote"] and not cooking["has_voted"]
    assert [e["state"] for e in cooking["items"]] == ["unavailable"] * 3  # nobody can vote yet
    too_early = client.post(f"/entries/{entry_ids[0]}/vote", headers=voter)
    assert too_early.status_code == 400 and too_early.json()["code"] == "voting_not_started"

    freeze(kst_at(1, 0, 1))  # cooking ended at kst_at(1, 0, 0); now 1h into the 24h voting window
    listing = client.get(f"/battles/{battle_id}/entries", headers=voter).json()
    assert listing["phase"] == "voting" and listing["participants"] == 3 and listing["can_vote"]
    assert [e["state"] for e in listing["items"]] == ["votable"] * 3
    assert [e["dish_name"] for e in listing["items"]] == ["요리0", "요리1", "요리2"]  # submission order
    mine = client.get(f"/battles/{battle_id}/entries", headers=c0).json()["items"]
    assert [e["state"] for e in mine] == ["mine", "votable", "votable"]

    own = client.post(f"/entries/{entry_ids[0]}/vote", headers=c0)
    assert own.status_code == 400 and own.json()["code"] == "own_entry"
    assert client.post(f"/entries/{entry_ids[0]}/vote", headers=outsider).json()["code"] == "wrong_group"
    assert client.post("/entries/999/vote", headers=voter).status_code == 404

    voted = client.post(f"/entries/{entry_ids[1]}/vote", headers=voter)
    assert voted.status_code == 200
    assert voted.json() == {"entry_id": entry_ids[1], "vote_count": 1, "has_voted": True, "points_awarded": 2}
    assert client.get("/me", headers=voter).json()["progress"]["points"] == 32  # 가입 30P + 투표 2P
    again = client.post(f"/entries/{entry_ids[2]}/vote", headers=voter)
    assert again.status_code == 409 and again.json()["code"] == "already_voted"
    assert client.get("/me", headers=voter).json()["progress"]["points"] == 32  # 두 번째는 안 줌
    after = client.get(f"/battles/{battle_id}/entries", headers=voter).json()
    assert after["has_voted"] and after["my_vote_entry_id"] == entry_ids[1]
    assert [e["state"] for e in after["items"]] == ["vote_done", "voted", "vote_done"]
    assert [e["vote_count"] for e in after["items"]] == [0, 1, 0]

    other_group = client.get(f"/battles/{battle_id}/entries", headers=outsider).json()
    assert other_group["can_vote"] is False and {e["state"] for e in other_group["items"]} == {"unavailable"}

    freeze(kst_at(1, 1, 1))  # voting window (24h from kst_at(1, 0, 0)) has closed
    late, _ = signup(client, "late@test.com", nickname="late", tier="intermediate")
    closed = client.post(f"/entries/{entry_ids[0]}/vote", headers=late)
    assert closed.status_code == 400 and closed.json()["code"] == "voting_closed"


# ------------------------------------------------------------------ battles: results
def test_finalization_ranks_ties_and_pays_points(client, freeze):
    cooks, voters, battle_id, entry_ids = run_battle(client, freeze, votes_for=(2, 2, 1, 0))
    assert client.get(f"/battles/{battle_id}/result", headers=cooks[0][0]).json()["code"] == "battle_not_finished"

    freeze(kst_at(1, 1, 1))  # past the 24h voting window
    result = client.get(f"/battles/{battle_id}/result", headers=cooks[1][0]).json()
    assert result["status"] == "ranked" and result["participants"] == 4 and result["tier_label"] == "중급"
    assert [(r["rank"], r["user"]["nickname"], r["vote_count"]) for r in result["podium"]] == [
        (1, "cook0", 2), (2, "cook1", 2), (3, "cook2", 1),
    ]
    assert [(r["rank"], r["tie"]) for r in result["top10"]] == [(1, "first"), (2, "tied"), (3, None), (4, None)]
    assert [r["is_me"] for r in result["top10"]] == [False, True, False, False]
    assert [r["is_winner"] for r in result["top10"]] == [True, False, False, False]  # tag on the 1등 row for everyone
    assert [r["can_share_recipe"] for r in result["top10"]] == [False] * 4  # cook1 isn't the winner: no share button
    winner_view = client.get(f"/battles/{battle_id}/result", headers=cooks[0][0]).json()
    assert [r["can_share_recipe"] for r in winner_view["top10"]] == [True, False, False, False]  # only the winner's own row
    assert result["top10"][0]["submitted_at"] < result["top10"][1]["submitted_at"]

    # 2등 +30P (100/60/40 순위 포인트, 참가자 4명 < 10명이라 절반): Lv.1 -> Lv.2
    assert result["me"] == {
        "joined": True, "rank": 2, "participation_points": 10, "rank_points": 30,
        "level_from": 1, "level_to": 2, "leveled_up": True, "can_share_recipe": False, "shared_recipe_id": None,
    }
    # each cook: 가입 30P + 참가 10P + 첫 대결 30P = 70P before rank points, then + (50/30/20/0 halved rank reward)
    balances = {}
    for (headers, user), expected in zip(cooks, [(120, 2), (100, 2), (90, 1), (70, 1)]):
        progress = client.get("/me", headers=headers).json()["progress"]
        balances[user["nickname"]] = (progress["total_points"], progress["level"])
        assert (progress["total_points"], progress["level"]) == expected
        assert progress["points"] == progress["total_points"]

    third = client.get(f"/battles/{battle_id}/result", headers=cooks[2][0]).json()["me"]
    assert (third["rank"], third["rank_points"], third["leveled_up"]) == (3, 20, False)
    last = client.get(f"/battles/{battle_id}/result", headers=cooks[3][0]).json()["me"]
    assert (last["rank"], last["rank_points"], last["participation_points"]) == (4, 0, 10)
    bystander = client.get(f"/battles/{battle_id}/result", headers=voters[0][0]).json()["me"]
    assert bystander["joined"] is False and bystander["rank"] is None and bystander["participation_points"] == 0

    # asking again (or hitting other screens) never pays twice
    client.get(f"/battles/{battle_id}/result", headers=cooks[0][0])
    client.get("/me/home", headers=cooks[1][0])
    assert client.get("/me", headers=cooks[1][0]).json()["progress"]["points"] == 100
    with SessionLocal() as db:
        assert db.scalar(select(func.sum(LedgerEntry.points_delta)).where(LedgerEntry.user_id == cooks[1][1]["id"])) == 100

    # the next week's battle points back at this one
    nxt = current_battle(client, cooks[1][0])
    assert nxt["id"] != battle_id
    assert nxt["last_result"] == {
        "battle_id": battle_id, "title": result["title"], "week_label": result["week_label"],
        "status": "ranked", "joined": True, "my_rank": 2,
    }
    assert current_battle(client, voters[0][0])["last_result"]["my_rank"] is None


def test_void_battle_when_fewer_than_three_join(client, freeze):
    cooks, voters, battle_id, _ = run_battle(client, freeze, votes_for=(1, 0))
    freeze(kst_at(1, 1, 1))  # past the 24h voting window
    result = client.get(f"/battles/{battle_id}/result", headers=cooks[0][0]).json()
    assert result["status"] == "void" and result["participants"] == 2
    assert result["podium"] == [] and result["top10"] == []
    assert result["me"]["rank"] is None and result["me"]["rank_points"] == 0 and result["me"]["participation_points"] == 10
    assert result["me"]["can_share_recipe"] is False
    progress = client.get("/me", headers=cooks[0][0]).json()["progress"]
    assert progress["points"] == 70  # 가입 30P + 참가 10P + 첫 대결 30P (순위 포인트는 없음)

    home = client.get("/me/home", headers=cooks[0][0]).json()
    assert [(h["status"], h["rank"]) for h in home["history"]] == [("void", None)]
    assert current_battle(client, cooks[0][0])["last_result"]["status"] == "void"


def test_home_stats_and_history(client, freeze):
    freeze(kst_at(0, 2, 12))
    a, me = signup(client, "a@test.com", nickname="Yuri", tier="intermediate")
    empty = client.get("/me/home", headers=a).json()
    assert empty["history"] == [] and empty["reviews"] == [] and empty["cooking_count_this_month"] == 0
    assert empty["saved_amount_krw"] == 0 and empty["me"]["nickname"] == "Yuri"

    battle = current_battle(client, a)
    join(client, a, battle["id"], dish="치즈 스크램블 에그")
    client.post("/recipes/1/reviews", json={"text": "김치가 신 게 더 맛있어요"}, headers=a)
    home = client.get("/me/home", headers=a).json()
    assert home["cooking_count_this_month"] == 1 and home["saved_amount_krw"] == 4000
    assert home["history"] == [{
        "battle_id": battle["id"], "entry_id": home["history"][0]["entry_id"], "title": battle["title"],
        "theme": battle["theme"], "week_label": battle["week_label"], "tier": "intermediate", "tier_label": "중급",
        "status": "in_progress", "rank": None,
    }]
    assert [(r["recipe_name"], r["text"]) for r in home["reviews"]] == [("김치볶음밥", "김치가 신 게 더 맛있어요")]
    assert home["review_total"] == 1 and home["me"]["review_count"] == 1
    assert [r["recipe_id"] for r in client.get("/me/reviews", headers=a).json()] == [1]


def test_notify_on_close_toggle(client, freeze):
    """참가 완료 화면의 [대회 종료 시 알림 받기]. MVP라 저장만 하고 실제 알림은 안 나가요."""
    freeze(kst_at(0, 2, 12))
    a, _ = signup(client, "a@test.com", tier="beginner")
    b, _ = signup(client, "b@test.com", tier="beginner")
    battle_id = current_battle(client, a)["id"]
    entry_id = join(client, a, battle_id).json()["entry"]["id"]
    assert current_battle(client, a)["my_entry"]["notify_on_close"] is False

    on = client.post(f"/entries/{entry_id}/notify", headers=a)
    assert on.status_code == 200 and on.json() == {"notify_on_close": True}
    assert current_battle(client, a)["my_entry"]["notify_on_close"] is True
    off = client.post(f"/entries/{entry_id}/notify", headers=a)  # toggles back off
    assert off.json() == {"notify_on_close": False}

    assert client.post(f"/entries/{entry_id}/notify", headers=b).status_code == 403  # not their entry
    assert client.post("/entries/999/notify", headers=a).status_code == 404


def test_home_history_survives_a_theme_battle_entry(client, freeze):
    """테마 대결은 tier가 없어서 홈 이력에 그대로 넣으면 죽기 쉬워요 — 안 죽는지 확인."""
    freeze(kst_at(0, 2, 12))
    a, _ = signup(client, "a@test.com", tier="beginner")
    theme_id = client.get("/battles/current", params={"kind": "theme"}, headers=a).json()["id"]
    join(client, a, theme_id)
    home = client.get("/me/home", headers=a).json()
    assert home["history"] == [{
        "battle_id": theme_id, "entry_id": home["history"][0]["entry_id"], "title": home["history"][0]["title"],
        "theme": home["history"][0]["theme"], "week_label": home["history"][0]["week_label"],
        "tier": None, "tier_label": None, "status": "in_progress", "rank": None,
    }]


def test_battle_home_bundles_daily_theme_and_voting_card(client, freeze):
    freeze(kst_at(0, 2, 12))
    a, _ = signup(client, "a@test.com", tier="intermediate")
    home = client.get("/battles/home", headers=a).json()
    assert home["daily"]["kind"] == "daily" and home["daily"]["tier"] == "intermediate"
    assert home["theme"]["kind"] == "theme" and home["theme"]["tier"] is None and home["theme"]["is_my_group"]
    assert home["voting"] is None  # nothing to vote on yet
    assert client.get("/battles/home").status_code == 401

    cooks, _, battle_id, _ = run_battle(client, freeze, votes_for=(1, 1, 1))  # leaves time mid-voting-window
    home2 = client.get("/battles/home", headers=cooks[0][0]).json()
    assert home2["voting"] == {
        "battle_id": battle_id, "kind": "daily", "title": home2["voting"]["title"],
        "group_label": "중급", "participants": 3, "hours_left": home2["voting"]["hours_left"], "has_voted": False,
    }
    assert 1 <= home2["voting"]["hours_left"] <= 23


# ------------------------------------------------------------------ google auth
def test_google_auth_requires_configuration(client):
    r = client.post("/auth/google", json={"id_token": "whatever"})
    assert r.status_code == 500 and r.json()["code"] == "google_not_configured"


def test_google_auth_rejects_bad_token(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "fake-client-id.apps.googleusercontent.com")
    r = client.post("/auth/google", json={"id_token": "not-a-real-jwt"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_google_token"


# ------------------------------------------------------------------ recipes
def test_seeded_recipes_and_filters(client):
    a, _ = signup(client, "a@test.com")

    def names(**params):
        page = client.get("/recipes", params=params, headers=a).json()
        return page["total"], sorted(r["name"] for r in page["items"])

    assert names()[0] == 8
    assert names(q="김치") == (1, ["김치볶음밥"])
    assert names(q="참치") == (1, ["참치마요 덮밥"])  # ingredient search
    assert names(q="밥 요리 대결")[0] == 1  # win label search
    assert names(q="%") == (0, [])  # LIKE wildcards are escaped
    assert names(category="rice")[0] == 2 and names(category=["rice", "dessert"])[0] == 3  # same group = OR
    assert names(budget="under_5000")[0] == 5 and names(budget="5000_to_10000")[0] == 2
    assert names(budget="over_10000") == (1, ["수제 라멘"])
    assert names(budget=["under_5000", "over_10000"])[0] == 6
    assert names(time="le_10")[0] == 2 and names(time="le_15")[0] == 5 and names(time="le_30")[0] == 7
    assert names(time="ge_60") == (1, ["수제 라멘"])
    assert names(difficulty="advanced") == (1, ["수제 라멘"]) and names(difficulty="beginner")[0] == 5
    assert names(tool="microwave") == (1, ["바나나 머그케이크"]) and names(tool="pan")[0] == 4
    assert names(budget="under_5000", difficulty="beginner")[0] == 4  # different groups = AND
    assert names(category="healthy", budget="under_5000") == (0, [])

    page = client.get("/recipes", params={"limit": 1}, headers=a).json()
    assert page["total"] == 8 and len(page["items"]) == 1 and page["has_more"] is True
    card = client.get("/recipes", params={"q": "크림"}, headers=a).json()["items"][0]
    assert card == {
        "id": card["id"], "name": "크림 파스타", "category": "pasta", "category_label": "파스타", "price": 4500,
        "minutes": 20, "difficulty": "intermediate", "difficulty_label": "중급", "win_label": "면 요리 대결 1등",
        "photo_url": None, "saves": 0, "is_saved": False, "is_essential": False,
    }
    assert names(essential="true") == (3, ["김치볶음밥", "비빔국수", "참치마요 덮밥"])  # "자취 필수" chip
    assert names(essential="true", time="le_10") == (1, ["참치마요 덮밥"])
    assert names(essential="false")[0] == 8  # only `true` narrows the list
    assert client.get("/recipes", params={"category": "sushi"}, headers=a).status_code == 422

    saved_id = client.get("/recipes", params={"q": "비빔국수"}, headers=a).json()["items"][0]["id"]
    client.post(f"/recipes/{saved_id}/save", headers=a)
    popular = client.get("/recipes", params={"sort": "popular"}, headers=a).json()["items"]
    assert popular[0]["id"] == saved_id and popular[0]["saves"] == 1 and popular[0]["is_saved"] is True


def test_recipe_detail_save_recent_and_reviews(client):
    a, _ = signup(client, "a@test.com", nickname="Yuri")
    b, _ = signup(client, "b@test.com", nickname="Minsu")
    kimchi = client.get("/recipes", params={"q": "김치볶음밥"}, headers=a).json()["items"][0]["id"]
    pasta = client.get("/recipes", params={"q": "크림"}, headers=a).json()["items"][0]["id"]

    detail = client.get(f"/recipes/{kimchi}", headers=a).json()
    assert (detail["name"], detail["price"], detail["minutes"], detail["difficulty_label"]) == ("김치볶음밥", 3500, 15, "초급")
    assert detail["author"]["nickname"] == "요리왕" and detail["win_label"] == "밥 요리 대결 1등"
    assert [(i["name"], i["amount"]) for i in detail["ingredients"]][:2] == [("김치", "1컵"), ("밥", "1공기")]
    assert [s["order"] for s in detail["steps"]] == [1, 2, 3] and detail["steps"][2]["text"] == "밥을 넣고 고루 볶는다."
    assert [i["name"] for i in detail["ingredients"]] == ["김치", "밥", "계란", "식용유"] and detail["is_essential"] is True
    assert detail["tools"] == [{"code": "pan", "label": "프라이팬 하나"}]
    assert detail["is_saved"] is False and detail["saves"] == 0 and detail["comment_count"] == 0
    assert client.get("/recipes/999", headers=a).status_code == 404

    assert client.post(f"/recipes/{kimchi}/save", headers=a).json() == {"saved": True, "saves": 1}
    assert client.post(f"/recipes/{kimchi}/save", headers=a).json()["saves"] == 1  # double tap is safe
    assert client.post(f"/recipes/{kimchi}/save", headers=b).json()["saves"] == 2
    client.post(f"/recipes/{pasta}/save", headers=a)
    saved = client.get("/me/saved-recipes", headers=a).json()
    assert saved["total"] == 2 and [r["id"] for r in saved["items"]] == [pasta, kimchi]  # newest save first
    assert client.get(f"/recipes/{kimchi}", headers=a).json()["is_saved"] is True
    assert client.get("/me", headers=a).json()["saved_recipe_count"] == 2
    assert client.delete(f"/recipes/{kimchi}/save", headers=a).json() == {"saved": False, "saves": 1}
    assert client.delete(f"/recipes/{kimchi}/save", headers=a).json()["saves"] == 1
    assert [r["id"] for r in client.get("/me/saved-recipes", headers=a).json()["items"]] == [pasta]

    client.get(f"/recipes/{pasta}", headers=b)
    client.get(f"/recipes/{kimchi}", headers=b)
    client.get(f"/recipes/{pasta}", headers=b)  # viewing again moves it back to the top
    recent = client.get("/me/recent-recipes", headers=b).json()["items"]
    assert [r["id"] for r in recent] == [pasta, kimchi]

    for who, text in ((a, "계란 반숙이 핵심이네요!"), (b, "오늘 저녁 메뉴 정했어요"), (a, "김치가 신 게 더 맛있어요")):
        created = client.post(f"/recipes/{kimchi}/reviews", json={"text": text}, headers=who)
        assert created.status_code == 201 and created.json()["is_mine"] is True
    listing = client.get(f"/recipes/{kimchi}/reviews", headers=b).json()
    assert listing["total"] == 3 and [r["text"] for r in listing["items"]][0] == "계란 반숙이 핵심이네요!"
    assert [r["author"]["nickname"] for r in listing["items"]] == ["Yuri", "Minsu", "Yuri"]
    assert [r["is_mine"] for r in listing["items"]] == [False, True, False]
    assert client.get(f"/recipes/{kimchi}", headers=b).json()["comment_count"] == 3
    assert client.post(f"/recipes/{kimchi}/reviews", json={"text": "  "}, headers=a).status_code == 422
    assert client.post("/recipes/999/reviews", json={"text": "x"}, headers=a).status_code == 404
    assert client.get("/me", headers=a).json()["review_count"] == 2


def test_winner_shares_recipe(client, freeze):
    cooks, voters, battle_id, entry_ids = run_battle(client, freeze, votes_for=(2, 1, 1))
    winner, runner_up = cooks[0][0], cooks[1][0]
    body = {
        "category": "noodle", "price": 4000, "minutes": 20, "difficulty": "intermediate", "tools": ["pan", "pan"],
        "ingredients": [{"name": "계란", "amount": "2개"}, {"name": "치즈"}], "steps": [{"text": "계란을 푼다"}, {"text": "익힌다"}],
    }

    early = client.post(f"/entries/{entry_ids[0]}/recipe", json=body, headers=winner)
    assert early.status_code == 403 and early.json()["code"] == "not_winner"  # not finalized yet (still voting)

    freeze(kst_at(1, 1, 1))  # past the 24h voting window
    result = client.get(f"/battles/{battle_id}/result", headers=winner).json()
    assert result["me"]["can_share_recipe"] is True
    assert client.post(f"/entries/{entry_ids[0]}/recipe", json=body, headers=runner_up).json()["code"] == "not_your_entry"
    assert client.post(f"/entries/{entry_ids[1]}/recipe", json=body, headers=runner_up).json()["code"] == "not_winner"
    assert client.post("/entries/999/recipe", json=body, headers=winner).status_code == 404
    assert client.post(f"/entries/{entry_ids[0]}/recipe", json={**body, "steps": []}, headers=winner).status_code == 422

    shared = client.post(f"/entries/{entry_ids[0]}/recipe", json=body, headers=winner)
    assert shared.status_code == 201
    recipe = shared.json()
    assert recipe["name"] == "요리0" and recipe["win_label"] == f"{result['theme']} 대결 1등"
    assert recipe["author"]["nickname"] == "cook0" and recipe["tools"] == [{"code": "pan", "label": "프라이팬 하나"}]
    assert [(i["name"], i["amount"]) for i in recipe["ingredients"]] == [("계란", "2개"), ("치즈", None)]
    assert recipe["photo_url"] and client.get(recipe["photo_url"]).status_code == 200

    again = client.post(f"/entries/{entry_ids[0]}/recipe", json=body, headers=winner)
    assert again.status_code == 409 and again.json()["code"] == "already_shared"
    me = client.get(f"/battles/{battle_id}/result", headers=winner).json()["me"]
    assert me["can_share_recipe"] is False and me["shared_recipe_id"] == recipe["id"]
    assert client.get("/recipes", params={"q": "요리0"}, headers=winner).json()["total"] == 1
    assert client.get("/recipes", headers=winner).json()["total"] == 9


# ------------------------------------------------------------------ shop
def test_shop_states_and_exchange(client):
    a, me = signup(client, "a@test.com")
    fresh = client.get("/shop", headers=a).json()
    assert fresh["points"] == 30 and fresh["level"] == 1  # signup bonus
    assert [(i["name"], i["price_points"], i["required_level"], i["state"], i["points_short"]) for i in fresh["items"]] == [
        ("편의점 1,000원권", 120, 1, "insufficient_points", 90),  # registration order, not price order
        ("아메리카노 기프티콘", 240, 2, "locked", 0),
        ("학식 식권", 650, 3, "locked", 0),
        ("치킨 기프티콘", 2600, 5, "locked", 0),
    ]
    convenience = next(i["id"] for i in fresh["items"] if i["name"] == "편의점 1,000원권")
    broke = client.post(f"/shop/items/{convenience}/exchange", headers=a)
    assert broke.status_code == 400 and broke.json()["code"] == "insufficient_points"

    set_user(me["id"], points=1500, total_points=1500)  # Lv.5
    rich = client.get("/shop", headers=a).json()
    states = {i["name"]: (i["state"], i["points_short"]) for i in rich["items"]}
    assert states["편의점 1,000원권"] == ("available", 0) and states["치킨 기프티콘"] == ("insufficient_points", 1100)

    chicken = next(i["id"] for i in rich["items"] if i["name"] == "치킨 기프티콘")
    done = client.post(f"/shop/items/{convenience}/exchange", headers=a)
    assert done.status_code == 201 and done.json() == {"item_name": "편의점 1,000원권", "points_spent": 120, "points": 1380}
    progress = client.get("/me", headers=a).json()["progress"]
    assert (progress["points"], progress["total_points"]) == (1380, 1500)  # spending never lowers the level
    assert client.post(f"/shop/items/{chicken}/exchange", headers=a).json()["code"] == "insufficient_points"
    assert client.post("/shop/items/999/exchange", headers=a).status_code == 404
    with SessionLocal() as db:
        assert [(e.name, e.points_spent) for e in db.scalars(select(Exchange).where(Exchange.user_id == me["id"]))] == [("편의점 1,000원권", 120)]
        assert db.scalar(select(func.sum(LedgerEntry.points_delta)).where(LedgerEntry.user_id == me["id"])) == -90  # +30 가입 - 120 교환
        assert db.get(User, me["id"]).points == 1380


def test_shop_monthly_safeguards(client):
    """상품별 월 재고 한도 · 1인당 월 교환 횟수 상한 (적자 방지)."""
    a, me_a = signup(client, "a@test.com")
    b, me_b = signup(client, "b@test.com")
    set_user(me_a["id"], points=10000, total_points=10000)
    set_user(me_b["id"], points=5000, total_points=5000)
    items = client.get("/shop", headers=a).json()["items"]
    chicken = next(i["id"] for i in items if i["name"] == "치킨 기프티콘")  # monthly_limit=10, price 2600

    assert client.post(f"/shop/items/{chicken}/exchange", headers=a).status_code == 201
    assert client.post(f"/shop/items/{chicken}/exchange", headers=a).status_code == 201  # 2회까지는 됨
    limited = client.post(f"/shop/items/{chicken}/exchange", headers=a)
    assert limited.status_code == 400 and limited.json()["code"] == "monthly_limit_reached"

    convenience = next(i["id"] for i in items if i["name"] == "편의점 1,000원권")  # monthly_limit=None
    assert client.post(f"/shop/items/{convenience}/exchange", headers=b).status_code == 201  # 다른 상품은 영향 없음


def test_locked_item_cannot_be_exchanged(client):
    a, me = signup(client, "a@test.com")
    set_user(me["id"], points=20, total_points=20)  # still Lv.1 in the new economy
    chicken = next(i["id"] for i in client.get("/shop", headers=a).json()["items"] if i["name"] == "치킨 기프티콘")
    locked = client.post(f"/shop/items/{chicken}/exchange", headers=a)
    assert locked.status_code == 403 and locked.json()["code"] == "level_locked" and "Lv.5" in locked.json()["detail"]
    assert client.get("/me", headers=a).json()["progress"]["points"] == 20


# ------------------------------------------------------------------ photo reuse detection (phash)
def test_photo_reuse_is_rejected(client):
    a, _ = signup(client, "a@test.com")
    b, _ = signup(client, "b@test.com")
    same_bytes = distinct_photo()
    first = client.post("/photos", files={"file": ("shot.png", same_bytes, "image/png")}, headers=a)
    assert first.status_code == 201

    reused_self = client.post("/photos", files={"file": ("shot.png", same_bytes, "image/png")}, headers=a)
    assert reused_self.status_code == 409 and reused_self.json()["code"] == "photo_reused"
    reused_other = client.post("/photos", files={"file": ("shot.png", same_bytes, "image/png")}, headers=b)
    assert reused_other.status_code == 409 and reused_other.json()["code"] == "photo_reused"

    import io as _io

    from PIL import Image as _Image

    resized = _io.BytesIO()
    _Image.open(_io.BytesIO(same_bytes)).resize((32, 32)).save(resized, "PNG")
    still_caught = client.post("/photos", files={"file": ("shot2.png", resized.getvalue(), "image/png")}, headers=a)
    assert still_caught.status_code == 409 and still_caught.json()["code"] == "photo_reused"

    assert camera_photo(client, a)["photo_id"]  # a genuinely different photo still goes through


# ------------------------------------------------------------------ entry comments + star ratings
def test_entry_comments_and_ratings(client, freeze):
    freeze(kst_at(0, 2, 12))
    a, _ = signup(client, "a@test.com", nickname="Yuri")
    b, _ = signup(client, "b@test.com", nickname="Minsu")
    c, _ = signup(client, "c@test.com", nickname="Somi")
    battle_id = current_battle(client, a)["id"]
    entry_id = join(client, a, battle_id).json()["entry"]["id"]

    assert client.get(f"/entries/{entry_id}/comments/mine", headers=b).json() is None
    own = client.post(f"/entries/{entry_id}/comments", json={"text": "셀프", "rating": 5}, headers=a)
    assert own.status_code == 400 and own.json()["code"] == "own_entry"

    assert client.post(f"/entries/{entry_id}/comments", json={"text": "맛있어 보여요", "rating": 5}, headers=b).status_code == 201
    dup = client.post(f"/entries/{entry_id}/comments", json={"text": "또", "rating": 4}, headers=b)
    assert dup.status_code == 409 and dup.json()["code"] == "already_reviewed"
    client.post(f"/entries/{entry_id}/comments", json={"text": "간이 좀 셀 듯", "rating": 3}, headers=c)

    listed = client.get(f"/entries/{entry_id}/comments", headers=a).json()
    assert listed["summary"] == {"average": 4.0, "count": 2, "distribution": {"5": 1, "4": 0, "3": 1, "2": 0, "1": 0}}
    assert [item["author"]["nickname"] for item in listed["items"]] == ["Somi", "Minsu"]  # latest first

    low_first = client.get(f"/entries/{entry_id}/comments", params={"sort": "rating_low"}, headers=a).json()
    assert [item["rating"] for item in low_first["items"]] == [3, 5]

    mine = client.get(f"/entries/{entry_id}/comments/mine", headers=b).json()
    edited = client.patch(f"/comments/{mine['id']}", json={"rating": 4}, headers=b)
    assert edited.status_code == 200 and edited.json()["rating"] == 4 and edited.json()["is_edited"]
    assert client.patch(f"/comments/{mine['id']}", json={"rating": 1}, headers=c).status_code == 403

    items = client.get(f"/battles/{battle_id}/entries", headers=a).json()["items"]
    mine_entry = next(i for i in items if i["id"] == entry_id)
    assert (mine_entry["rating_count"], mine_entry["comment_count"]) == (2, 2)

    client.delete(f"/comments/{mine['id']}", headers=b)
    assert client.get(f"/entries/{entry_id}/comments/mine", headers=b).json() is None


# ------------------------------------------------------------------ admin: demo phase/close tools
def test_admin_only_and_phase_close_tools(client, freeze, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "admin_emails", "admin@test.com")
    freeze(kst_at(0, 2, 12))
    admin, _ = signup(client, "admin@test.com", nickname="Admin")
    a, _ = signup(client, "a@test.com")
    b, _ = signup(client, "b@test.com")
    c, _ = signup(client, "c@test.com")
    assert client.get("/me", headers=admin).json()["progress"] is not None

    battle_id = current_battle(client, a)["id"]
    denied = client.post(f"/admin/battles/{battle_id}/phase", json={"phase": "voting"}, headers=a)
    assert denied.status_code == 403 and denied.json()["code"] == "admin_only"

    entry_ids = [join(client, h, battle_id).json()["entry"]["id"] for h in (a, b, c)]

    moved = client.post(f"/admin/battles/{battle_id}/phase", json={"phase": "voting"}, headers=admin)
    assert moved.status_code == 200 and moved.json()["phase"] == "voting"
    assert client.get(f"/battles/{battle_id}/entries", headers=a).json()["can_vote"]
    client.post(f"/entries/{entry_ids[0]}/vote", headers=b)

    closed = client.post(f"/admin/battles/{battle_id}/close", headers=admin)
    assert closed.status_code == 200 and closed.json() == {
        "battle_id": battle_id, "finalized": True, "is_void": False, "participants": 3,
    }
    already = client.post(f"/admin/battles/{battle_id}/close", headers=admin)
    assert already.status_code == 400 and already.json()["code"] == "battle_already_finalized"

    result = client.get(f"/battles/{battle_id}/result", headers=a).json()
    assert result["status"] == "ranked" and result["podium"][0]["entry_id"] == entry_ids[0]

    new_item = client.post(
        "/admin/shop/items", json={"name": "테스트 쿠폰", "price_points": 5, "required_level": 1, "monthly_limit": 1},
        headers=admin,
    )
    assert new_item.status_code == 201 and new_item.json()["monthly_limit"] == 1
    assert client.post("/admin/shop/items", json={"name": "x", "price_points": 1}, headers=a).status_code == 403


# ------------------------------------------------------------------ streak bonus / review cap / expiry
def test_streak_bonus_after_three_weeks(client, freeze):
    a, me_a = signup(client, "a@test.com")
    b, _ = signup(client, "b@test.com")
    c, _ = signup(client, "c@test.com")
    for week in range(3):
        freeze(kst_at(week, 2, 12))
        bid = current_battle(client, a)["id"]
        join(client, a, bid)
        join(client, b, bid)
        join(client, c, bid)
    # Joining week N+1 auto-finalizes week N's battle (and pays rank points for it), so check the
    # streak bonus directly in the ledger instead of trying to predict the total balance.
    with SessionLocal() as db:
        streaks = db.scalars(
            select(LedgerEntry).where(LedgerEntry.user_id == me_a["id"], LedgerEntry.reason == "streak")
        ).all()
        assert [s.points_delta for s in streaks] == [20]  # exactly once, on the 3rd consecutive week


def test_review_points_daily_cap(client):
    a, _ = signup(client, "a@test.com")
    b, _ = signup(client, "b@test.com")
    recipe_id = client.get("/recipes", headers=a).json()["items"][0]["id"]
    before = client.get("/me", headers=b).json()["progress"]["points"]
    for i in range(4):
        assert client.post(f"/recipes/{recipe_id}/reviews", json={"text": f"후기{i}"}, headers=b).status_code == 201
    after = client.get("/me", headers=b).json()["progress"]["points"]
    assert after - before == 3  # REVIEW_DAILY_CAP, 4번째는 지급 안 됨


def test_point_expiry_after_a_year(client):
    a, me = signup(client, "a@test.com")
    with SessionLocal() as db:
        row = db.scalar(select(LedgerEntry).where(LedgerEntry.user_id == me["id"], LedgerEntry.reason == "signup"))
        row.created_at = row.created_at - dt.timedelta(days=366)
        db.commit()
    progress = client.get("/me", headers=a).json()["progress"]
    assert progress["points"] == 0 and progress["total_points"] == 30  # 보유 포인트만 소멸, 누적·레벨은 그대로
