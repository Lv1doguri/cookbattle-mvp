import datetime as dt

from app.database import SessionLocal
from app.enums import Tier
from app.models import Exchange, LedgerEntry, User
from app.services.battles import get_or_create_battle, week_label
from app.services.points import level_for
from sqlalchemy import func, select

from .conftest import PASSWORD, PNG, current_battle, group, join, kst_at, set_user, signup


def _iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def run_battle(client, freeze, votes_for=(2, 2, 1, 0)):
    """One finished-voting battle in the 중급 group. votes_for[i] = votes cook_i receives.

    cook0 submits first, cook1 second, ... Voters are separate non-participants. Time is left
    frozen mid-week; call freeze(kst_at(1, 0, 1)) afterwards to end the battle.
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
    freeze(kst_at(0, 4, 12))
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
        "level": 1, "points": 0, "total_points": 0, "level_start_points": 0, "next_level_points": 5, "points_to_next_level": 5,
    }
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
    assert [level_for(p) for p in (0, 4, 5, 14, 15, 29, 30, 49, 50)] == [1, 1, 2, 2, 3, 3, 4, 4, 5]


def test_progress_matches_the_home_mockup(client):
    _, me = signup(client, "a@test.com", tier="intermediate")
    set_user(me["id"], points=9, total_points=9)
    headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'email': 'a@test.com', 'password': PASSWORD}).json()['access_token']}"}
    progress = client.get("/me", headers=headers).json()["progress"]
    assert progress["level"] == 2 and progress["next_level_points"] == 15 and progress["points_to_next_level"] == 6  # "다음 레벨까지 6P → Lv.3"


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


# ------------------------------------------------------------------ battles: setup
def test_weekly_battle_schedule(client):
    with SessionLocal() as db:
        battle = get_or_create_battle(db, Tier.intermediate, dt.datetime(2026, 9, 23, 3, 0, tzinfo=dt.timezone.utc))
        assert battle.theme == "계란 요리" and battle.description == "계란이 메인인 든든한 한 끼"
        assert battle.starts_at == dt.datetime(2026, 9, 20, 15, 0, tzinfo=dt.timezone.utc)  # Mon 9/21 00:00 KST
        assert battle.ends_at == dt.datetime(2026, 9, 27, 15, 0, tzinfo=dt.timezone.utc)  # Mon 9/28 00:00 KST
        beginner = get_or_create_battle(db, Tier.beginner, dt.datetime(2026, 9, 23, 3, 0, tzinfo=dt.timezone.utc))
        assert beginner.id != battle.id and beginner.description == "간단한 계란 요리면 OK"
        assert get_or_create_battle(db, Tier.intermediate, dt.datetime(2026, 9, 25, 3, 0, tzinfo=dt.timezone.utc)).id == battle.id
    assert week_label(dt.date(2026, 9, 21)) == "9월 4주차"
    assert week_label(dt.date(2026, 8, 31)) == "9월 1주차"  # its Thursday is Sep 3


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

    no_photo = client.post(f"/battles/{view['id']}/entries", data={"dish_name": "요리"}, headers=inter)
    assert no_photo.status_code == 422
    not_image = client.post(
        f"/battles/{view['id']}/entries", data={"dish_name": "요리"}, files={"photo": ("a.png", b"nope", "image/png")}, headers=inter
    )
    assert not_image.status_code == 400 and not_image.json()["code"] == "unsupported_image"
    blank = join(client, inter, view["id"], dish="   ")
    assert blank.status_code == 422

    joined = join(client, inter, view["id"], dish="치즈 스크램블 에그", description="치즈는 마지막에!")
    assert joined.status_code == 201
    body = joined.json()
    assert (body["points_awarded"], body["points"]) == (1, 1)
    assert body["entry"]["dish_name"] == "치즈 스크램블 에그" and body["entry"]["state"] == "mine"
    assert body["entry"]["author"]["nickname"] == "u_b" and client.get(body["entry"]["photo_url"]).status_code == 200

    again = join(client, inter, view["id"])
    assert again.status_code == 409 and again.json()["code"] == "already_entered"
    after = current_battle(client, inter)
    assert after["can_join"] is False and after["has_joined"] and after["participants"] == 1
    assert after["my_entry"]["id"] == body["entry"]["id"]
    assert client.get("/me", headers=inter).json()["progress"]["points"] == 1

    freeze(kst_at(1, 0, 1))  # the week is over
    late, _ = signup(client, "c@test.com", tier="intermediate")
    closed = join(client, late, view["id"])
    assert closed.status_code == 400 and closed.json()["code"] == "battle_closed"


# ------------------------------------------------------------------ battles: voting
def test_voting_rules(client, freeze):
    freeze(kst_at(0, 2, 12))
    (c0, _), (c1, _), (c2, _) = group(client, 3, prefix="cook")
    voter, _ = signup(client, "voter@test.com", nickname="voter", tier="intermediate")
    outsider, _ = signup(client, "out@test.com", nickname="outsider", tier="beginner")
    battle_id = current_battle(client, c0)["id"]
    entry_ids = [join(client, h, battle_id, dish=f"요리{i}").json()["entry"]["id"] for i, h in enumerate((c0, c1, c2))]

    listing = client.get(f"/battles/{battle_id}/entries", headers=voter).json()
    assert listing["participants"] == 3 and listing["can_vote"] and not listing["has_voted"] and listing["is_open"]
    assert [e["state"] for e in listing["items"]] == ["votable"] * 3
    assert [e["dish_name"] for e in listing["items"]] == ["요리0", "요리1", "요리2"]  # submission order
    mine = client.get(f"/battles/{battle_id}/entries", headers=c0).json()["items"]
    assert [e["state"] for e in mine] == ["mine", "votable", "votable"]

    own = client.post(f"/entries/{entry_ids[0]}/vote", headers=c0)
    assert own.status_code == 400 and own.json()["code"] == "own_entry"
    assert client.post(f"/entries/{entry_ids[0]}/vote", headers=outsider).json()["code"] == "wrong_group"
    assert client.post("/entries/999/vote", headers=voter).status_code == 404

    voted = client.post(f"/entries/{entry_ids[1]}/vote", headers=voter)
    assert voted.status_code == 200 and voted.json() == {"entry_id": entry_ids[1], "vote_count": 1, "has_voted": True}
    again = client.post(f"/entries/{entry_ids[2]}/vote", headers=voter)
    assert again.status_code == 409 and again.json()["code"] == "already_voted"
    after = client.get(f"/battles/{battle_id}/entries", headers=voter).json()
    assert after["has_voted"] and after["my_vote_entry_id"] == entry_ids[1]
    assert [e["state"] for e in after["items"]] == ["vote_done", "voted", "vote_done"]
    assert [e["vote_count"] for e in after["items"]] == [0, 1, 0]

    other_group = client.get(f"/battles/{battle_id}/entries", headers=outsider).json()
    assert other_group["can_vote"] is False and {e["state"] for e in other_group["items"]} == {"unavailable"}

    freeze(kst_at(1, 0, 1))
    late, _ = signup(client, "late@test.com", nickname="late", tier="intermediate")
    closed = client.post(f"/entries/{entry_ids[0]}/vote", headers=late)
    assert closed.status_code == 400 and closed.json()["code"] == "battle_closed"


# ------------------------------------------------------------------ battles: results
def test_finalization_ranks_ties_and_pays_points(client, freeze):
    cooks, voters, battle_id, entry_ids = run_battle(client, freeze, votes_for=(2, 2, 1, 0))
    assert client.get(f"/battles/{battle_id}/result", headers=cooks[0][0]).json()["code"] == "battle_not_finished"

    freeze(kst_at(1, 0, 1))
    result = client.get(f"/battles/{battle_id}/result", headers=cooks[1][0]).json()
    assert result["status"] == "ranked" and result["participants"] == 4 and result["tier_label"] == "중급"
    assert [(r["rank"], r["user"]["nickname"], r["vote_count"]) for r in result["podium"]] == [
        (1, "cook0", 2), (2, "cook1", 2), (3, "cook2", 1),
    ]
    assert [(r["rank"], r["tie"]) for r in result["top10"]] == [(1, "first"), (2, "tied"), (3, None), (4, None)]
    assert [r["is_me"] for r in result["top10"]] == [False, True, False, False]
    assert [r["can_share_recipe"] for r in result["top10"]] == [True, False, False, False]
    assert result["top10"][0]["submitted_at"] < result["top10"][1]["submitted_at"]

    # 2등 +4P: Lv.1 -> Lv.2, exactly the result mock-up
    assert result["me"] == {
        "joined": True, "rank": 2, "participation_points": 1, "rank_points": 4,
        "level_from": 1, "level_to": 2, "leveled_up": True, "can_share_recipe": False, "shared_recipe_id": None,
    }
    balances = {}
    for (headers, user), expected in zip(cooks, [(6, 2), (5, 2), (4, 1), (1, 1)]):
        progress = client.get("/me", headers=headers).json()["progress"]
        balances[user["nickname"]] = (progress["total_points"], progress["level"])
        assert (progress["total_points"], progress["level"]) == expected
        assert progress["points"] == progress["total_points"]

    third = client.get(f"/battles/{battle_id}/result", headers=cooks[2][0]).json()["me"]
    assert (third["rank"], third["rank_points"], third["leveled_up"]) == (3, 3, False)
    last = client.get(f"/battles/{battle_id}/result", headers=cooks[3][0]).json()["me"]
    assert (last["rank"], last["rank_points"], last["participation_points"]) == (4, 0, 1)
    bystander = client.get(f"/battles/{battle_id}/result", headers=voters[0][0]).json()["me"]
    assert bystander["joined"] is False and bystander["rank"] is None and bystander["participation_points"] == 0

    # asking again (or hitting other screens) never pays twice
    client.get(f"/battles/{battle_id}/result", headers=cooks[0][0])
    client.get("/me/home", headers=cooks[1][0])
    assert client.get("/me", headers=cooks[1][0]).json()["progress"]["points"] == 5
    with SessionLocal() as db:
        assert db.scalar(select(func.sum(LedgerEntry.points_delta)).where(LedgerEntry.user_id == cooks[1][1]["id"])) == 5

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
    freeze(kst_at(1, 0, 1))
    result = client.get(f"/battles/{battle_id}/result", headers=cooks[0][0]).json()
    assert result["status"] == "void" and result["participants"] == 2
    assert result["podium"] == [] and result["top10"] == []
    assert result["me"]["rank"] is None and result["me"]["rank_points"] == 0 and result["me"]["participation_points"] == 1
    assert result["me"]["can_share_recipe"] is False
    progress = client.get("/me", headers=cooks[0][0]).json()["progress"]
    assert progress["points"] == 1  # the participation point is still theirs

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
        "photo_url": None, "saves": 0, "is_saved": False,
    }
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
    assert [s["order"] for s in detail["steps"]] == [1, 2, 3, 4] and detail["steps"][3]["text"] == "계란 프라이를 올려 완성한다."
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
    assert early.status_code == 403 and early.json()["code"] == "not_winner"  # battle still running

    freeze(kst_at(1, 0, 1))
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
    assert fresh["points"] == 0 and fresh["level"] == 1
    assert [(i["name"], i["price_points"], i["required_level"], i["state"], i["points_short"]) for i in fresh["items"]] == [
        ("학식 식권", 800, 1, "insufficient_points", 800),
        ("커피 기프티콘", 1000, 1, "insufficient_points", 1000),
        ("편의점 상품권", 3000, 2, "locked", 0),
        ("치킨 기프티콘", 5000, 5, "locked", 0),
    ]
    coffee = next(i["id"] for i in fresh["items"] if i["name"] == "커피 기프티콘")
    broke = client.post(f"/shop/items/{coffee}/exchange", headers=a)
    assert broke.status_code == 400 and broke.json()["code"] == "insufficient_points"

    set_user(me["id"], points=1240, total_points=1240)
    rich = client.get("/shop", headers=a).json()
    states = {i["name"]: (i["state"], i["points_short"]) for i in rich["items"]}
    assert states["커피 기프티콘"] == ("available", 0) and states["편의점 상품권"] == ("insufficient_points", 1760)  # "1,760P 더 필요해요"

    done = client.post(f"/shop/items/{coffee}/exchange", headers=a)
    assert done.status_code == 201 and done.json() == {"item_name": "커피 기프티콘", "points_spent": 1000, "points": 240}
    progress = client.get("/me", headers=a).json()["progress"]
    assert (progress["points"], progress["total_points"]) == (240, 1240)  # spending never lowers the level
    assert client.post(f"/shop/items/{coffee}/exchange", headers=a).json()["code"] == "insufficient_points"
    assert client.post("/shop/items/999/exchange", headers=a).status_code == 404
    with SessionLocal() as db:
        assert [(e.name, e.points_spent) for e in db.scalars(select(Exchange).where(Exchange.user_id == me["id"]))] == [("커피 기프티콘", 1000)]
        assert db.scalar(select(func.sum(LedgerEntry.points_delta)).where(LedgerEntry.user_id == me["id"])) == -1000
        assert db.get(User, me["id"]).points == 240


def test_locked_item_cannot_be_exchanged(client):
    a, me = signup(client, "a@test.com")
    set_user(me["id"], points=20, total_points=20)  # Lv.3
    chicken = next(i["id"] for i in client.get("/shop", headers=a).json()["items"] if i["name"] == "치킨 기프티콘")
    locked = client.post(f"/shop/items/{chicken}/exchange", headers=a)
    assert locked.status_code == 403 and locked.json()["code"] == "level_locked" and "Lv.5" in locked.json()["detail"]
    assert client.get("/me", headers=a).json()["progress"]["points"] == 20
