import datetime as dt

from app.database import SessionLocal
from app.models import LedgerEntry, User
from sqlalchemy import select

from .conftest import PASSWORD, kst_noon, make_post, new_photo, post_body, set_user, signup


# ------------------------------------------------------------------ auth / profile
def test_signup_login_and_me(client):
    r = client.post("/auth/signup", json={"email": "Yuri@Test.com", "password": PASSWORD})
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["email"] == "yuri@test.com"
    assert user["nickname"] == "yuri"
    assert user["handle"] == "yuri"
    assert user["needs_tier_selection"] is True
    assert user["coins"] == 0
    assert user["progress"]["level"] == 1

    dup = client.post("/auth/signup", json={"email": "yuri@test.com", "password": PASSWORD})
    assert dup.status_code == 409 and dup.json()["code"] == "email_taken"

    wrong = client.post("/auth/login", json={"email": "yuri@test.com", "password": "wrong-password"})
    assert wrong.status_code == 401 and wrong.json()["code"] == "invalid_credentials"
    unknown = client.post("/auth/login", json={"email": "nobody@test.com", "password": PASSWORD})
    assert unknown.status_code == 401 and unknown.json()["detail"] == wrong.json()["detail"]

    ok = client.post("/auth/login", json={"email": "YURI@test.com", "password": PASSWORD})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()["id"] == user["id"]
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_errors_are_always_strings(client):
    r = client.post("/auth/signup", json={"email": "a@test.com", "password": "short"})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str) and r.json()["code"] == "validation_error"
    assert client.get("/nope").json()["detail"] == "Not Found"


def test_handle_generation_avoids_collisions(client):
    _, a = signup(client, "yuri@a.com")
    _, b = signup(client, "yuri@b.com")
    assert a["handle"] == "yuri" and b["handle"] != "yuri" and b["handle"].startswith("yuri")
    _, korean = signup(client, "hangul@a.com", nickname="유리")
    assert korean["nickname"] == "유리" and korean["handle"].startswith("hangul")


def test_tier_selection_and_profile_edit(client):
    h, me = signup(client, "a@test.com")
    _, other = signup(client, "b@test.com")

    tiered = client.put("/me/tier", json={"tier": "intermediate"}, headers=h).json()
    assert tiered["tier"] == "intermediate" and tiered["tier_label"] == "중급"
    assert tiered["needs_tier_selection"] is False
    assert client.put("/me/tier", json={"tier": "expert"}, headers=h).status_code == 422

    taken = client.patch("/me", json={"handle": other["handle"]}, headers=h)
    assert taken.status_code == 409 and taken.json()["code"] == "handle_taken"
    edited = client.patch(
        "/me", json={"nickname": "Yuri", "bio": "자취 2년차", "handle": "yuri_cooks"}, headers=h
    ).json()
    assert (edited["nickname"], edited["bio"], edited["handle"]) == ("Yuri", "자취 2년차", "yuri_cooks")
    assert client.patch("/me", json={"handle": "Bad Handle!"}, headers=h).status_code == 422


# ------------------------------------------------------------------ photos
def test_photo_upload_validation(client):
    h, _ = signup(client, "a@test.com")
    bad = client.post("/photos", files={"file": ("x.png", b"not an image at all", "image/png")}, headers=h)
    assert bad.status_code == 400 and bad.json()["code"] == "unsupported_image"
    assert client.post("/photos", files={"file": ("x.png", b"\x89PNG\r\n\x1a\n00", "image/png")}).status_code == 401

    ok = client.post("/photos", files={"file": ("x.png", b"\x89PNG\r\n\x1a\n" + b"0" * 10, "image/png")}, headers=h)
    body = ok.json()
    assert ok.status_code == 201 and body["photo_url"].startswith("/uploads/") and body["photo_url"].endswith(".png")
    assert client.get(body["photo_url"]).status_code == 200


# ------------------------------------------------------------------ posting + rewards
def test_post_rewards_progress_and_daily_cap(client):
    h, me = signup(client, "a@test.com", tier="intermediate")

    first = make_post(client, h)
    assert first["reward"] == {
        "xp": 50, "coins": 30, "is_battle_entry": False, "daily_limit_reached": False, "leveled_up": False,
    }
    assert first["progress"]["xp"] == 50 and first["coins"] == 30
    post = first["post"]
    assert post["recipe"]["title"] == "크림 파스타" and post["recipe"]["ingredient_count"] == 3
    assert post["recipe"]["difficulty_label"] == "중급" and post["is_mine"] is True

    make_post(client, h)
    make_post(client, h)
    capped = make_post(client, h)
    assert capped["reward"]["xp"] == 0 and capped["reward"]["daily_limit_reached"] is True
    mine = client.get("/me", headers=h).json()
    assert mine["progress"]["xp"] == 150 and mine["coins"] == 90 and mine["post_count"] == 4


def test_done_screen_numbers_and_level_up(client):
    h, me = signup(client, "a@test.com", tier="intermediate")
    set_user(me["id"], xp=1250)
    done = make_post(client, h)
    assert done["progress"] == {
        "tier": "intermediate", "tier_label": "중급", "level": 3, "xp": 1300,
        "level_start_xp": 1000, "next_level_xp": 1500, "xp_to_next_level": 200,
    }
    assert done["reward"]["leveled_up"] is False

    h2, me2 = signup(client, "b@test.com", tier="beginner")
    set_user(me2["id"], xp=480)
    assert make_post(client, h2)["reward"]["leveled_up"] is True


def test_photo_rules(client, freeze):
    freeze(kst_noon())
    h, _ = signup(client, "a@test.com", tier="beginner")
    other, _ = signup(client, "b@test.com", tier="beginner")

    photo_id = new_photo(client, h)
    assert client.post("/posts", json=post_body(photo_id), headers=other).status_code == 404  # not their photo
    assert client.post("/posts", json=post_body(photo_id), headers=h).status_code == 201
    reuse = client.post("/posts", json=post_body(photo_id), headers=h)
    assert reuse.status_code == 409 and reuse.json()["code"] == "photo_already_used"

    stale = new_photo(client, h)
    freeze(kst_noon() + dt.timedelta(hours=2))
    expired = client.post("/posts", json=post_body(stale), headers=h)
    assert expired.status_code == 400 and expired.json()["code"] == "photo_expired"


def test_post_validation(client):
    h, _ = signup(client, "a@test.com", tier="beginner")
    pid = new_photo(client, h)
    for bad in ({"ingredients": []}, {"steps": []}, {"cost_krw": -1}, {"title": "  "}, {"difficulty": "god"}):
        assert client.post("/posts", json=post_body(pid, **bad), headers=h).status_code == 422, bad


# ------------------------------------------------------------------ battles
def test_battle_join_rules(client, freeze):
    freeze(kst_noon())
    beginner, _ = signup(client, "a@test.com", tier="beginner")
    inter, _ = signup(client, "b@test.com", tier="intermediate")

    view = client.get("/battles/today?tier=intermediate", headers=inter).json()
    assert view["reward_xp"] == 200 and view["reward_coins"] == 80 and view["tier_label"] == "중급"
    assert view["is_my_tier"] and view["can_join"] and view["participants"] == 0 and view["my_entry"] is None
    assert view["seconds_left"] == 12 * 3600 and len(view["weekly_challenge"]) == 7
    assert sum(d["is_today"] for d in view["weekly_challenge"]) == 1
    assert client.get("/battles/today?tier=beginner", headers=inter).json()["can_join"] is False
    default_tier = client.get("/battles/today", headers=beginner).json()
    assert default_tier["tier"] == "beginner" and default_tier["reward_xp"] == 150

    wrong = client.post("/posts", json=post_body(new_photo(client, beginner), battle_id=view["id"]), headers=beginner)
    assert wrong.status_code == 403 and wrong.json()["code"] == "wrong_tier"

    joined = make_post(client, inter, battle_id=view["id"])
    assert joined["reward"]["xp"] == 200 and joined["reward"]["coins"] == 80 and joined["reward"]["is_battle_entry"]
    assert joined["post"]["battle_id"] == view["id"]
    again = client.post("/posts", json=post_body(new_photo(client, inter), battle_id=view["id"]), headers=inter)
    assert again.status_code == 409 and again.json()["code"] == "already_entered"

    after = client.get("/battles/today?tier=intermediate", headers=inter).json()
    assert after["can_join"] is False and after["participants"] == 1
    assert after["my_entry"] == {"post_id": joined["post"]["id"], "xp": 200, "rank": 1}

    # a different day's battle is a different battle
    late, _ = signup(client, "c@test.com", tier="intermediate")
    freeze(kst_noon() + dt.timedelta(hours=13))  # past KST midnight
    closed = client.post("/posts", json=post_body(new_photo(client, late), battle_id=view["id"]), headers=late)
    assert closed.status_code == 400 and closed.json()["code"] == "battle_closed"


def test_leaderboard_ranking_and_like_xp(client, freeze):
    freeze(kst_noon())
    heads, users = [], []
    for i in range(3):
        h, u = signup(client, f"u{i}@test.com", tier="intermediate", nickname=f"cook{i}")
        heads.append(h)
        users.append(u)
    fan, _ = signup(client, "fan@test.com", tier="beginner")

    battle_id = client.get("/battles/today?tier=intermediate", headers=heads[0]).json()["id"]
    post_ids = []
    for i, h in enumerate(heads):
        freeze(kst_noon() + dt.timedelta(minutes=i))  # distinct entry times: u0 earliest
        post_ids.append(make_post(client, h, battle_id=battle_id)["post"]["id"])
    freeze(kst_noon() + dt.timedelta(minutes=10))

    def board(headers, limit=50):
        return client.get(f"/battles/{battle_id}/leaderboard?limit={limit}", headers=headers).json()

    assert [e["user"]["nickname"] for e in board(fan)["entries"]] == ["cook0", "cook1", "cook2"]

    assert client.post(f"/posts/{post_ids[1]}/like", headers=fan).json() == {"liked": True, "like_count": 1}
    client.post(f"/posts/{post_ids[2]}/like", headers=fan)
    client.post(f"/posts/{post_ids[1]}/like", headers=heads[1])  # self-like: counts as a like, pays nothing
    top = board(heads[0])
    assert [(e["user"]["nickname"], e["xp"]) for e in top["entries"]] == [("cook1", 210), ("cook2", 210), ("cook0", 200)]
    assert top["participants"] == 3 and [e["rank"] for e in top["entries"]] == [1, 2, 3]
    assert top["me"] == {"rank": 3, "xp": 200, "xp_to_next_rank": 10}  # cook0 entered first, so tying is enough
    assert client.get("/me", headers=heads[1]).json()["progress"]["xp"] == 210

    assert board(heads[2])["me"]["xp_to_next_rank"] == 1  # cook2 entered after cook1, must beat them
    assert board(heads[1])["me"] == {"rank": 1, "xp": 210, "xp_to_next_rank": 0}
    assert board(fan)["me"] is None
    assert len(board(fan, limit=2)["entries"]) == 2

    # likes are idempotent; un-liking takes the XP back
    assert client.post(f"/posts/{post_ids[2]}/like", headers=fan).json()["like_count"] == 1
    assert client.delete(f"/posts/{post_ids[1]}/like", headers=fan).json() == {"liked": False, "like_count": 1}
    assert client.delete(f"/posts/{post_ids[1]}/like", headers=fan).json()["like_count"] == 1
    assert client.get("/me", headers=heads[1]).json()["progress"]["xp"] == 200
    assert [e["xp"] for e in board(fan)["entries"]] == [210, 200, 200]


def test_likes_after_battle_end_pay_nothing(client, freeze):
    freeze(kst_noon())
    h, me = signup(client, "a@test.com", tier="intermediate")
    fan, _ = signup(client, "fan@test.com")
    battle_id = client.get("/battles/today", headers=h).json()["id"]
    post_id = make_post(client, h, battle_id=battle_id)["post"]["id"]

    freeze(kst_noon() + dt.timedelta(hours=13))
    assert client.post(f"/posts/{post_id}/like", headers=fan).json()["like_count"] == 1
    assert client.get("/me", headers=h).json()["progress"]["xp"] == 200
    client.delete(f"/posts/{post_id}/like", headers=fan)
    assert client.get("/me", headers=h).json()["progress"]["xp"] == 200  # nothing was paid, nothing is taken back


# ------------------------------------------------------------------ social
def test_feed_follow_and_profiles(client):
    a, a_user = signup(client, "a@test.com", tier="beginner")
    b, b_user = signup(client, "b@test.com", tier="beginner")
    c, c_user = signup(client, "c@test.com", tier="beginner")
    b_post = make_post(client, b)["post"]["id"]
    c_post = make_post(client, c)["post"]["id"]

    everyone = client.get("/feed", headers=a).json()
    assert [p["id"] for p in everyone["items"]] == [c_post, b_post] and everyone["has_more"] is False
    assert client.get("/feed?tab=following", headers=a).json()["items"] == []
    assert client.get("/feed?limit=1", headers=a).json()["has_more"] is True

    assert client.post(f"/users/{a_user['id']}/follow", headers=a).status_code == 400
    assert client.post(f"/users/{b_user['id']}/follow", headers=a).json() == {"following": True, "follower_count": 1}
    assert client.post(f"/users/{b_user['id']}/follow", headers=a).json()["follower_count"] == 1
    following = client.get("/feed?tab=following", headers=a).json()["items"]
    assert [p["id"] for p in following] == [b_post] and following[0]["is_following_author"] is True

    detail = client.get(f"/posts/{b_post}", headers=a).json()
    assert detail["author_follower_count"] == 1
    profile = client.get(f"/users/{b_user['id']}", headers=a).json()
    assert profile["is_following"] and profile["follower_count"] == 1 and profile["post_count"] == 1
    assert "coins" not in profile and "email" not in profile
    assert [p["id"] for p in client.get(f"/users/{b_user['id']}/posts", headers=a).json()["items"]] == [b_post]
    assert client.get("/users/999", headers=a).status_code == 404

    assert client.delete(f"/users/{b_user['id']}/follow", headers=a).json() == {"following": False, "follower_count": 0}
    assert client.get("/feed?tab=following", headers=a).json()["items"] == []


def test_like_and_save_lists(client):
    a, _ = signup(client, "a@test.com", tier="beginner")
    b, _ = signup(client, "b@test.com", tier="beginner")
    post_id = make_post(client, b)["post"]["id"]

    assert client.post(f"/posts/{post_id}/like", headers=a).json() == {"liked": True, "like_count": 1}
    assert client.post(f"/posts/{post_id}/save", headers=a).json() == {"saved": True, "save_count": 1}
    client.post(f"/posts/{post_id}/save", headers=a)  # idempotent
    liked = client.get("/me/likes", headers=a).json()["items"]
    saved = client.get("/me/saved", headers=a).json()["items"]
    assert [p["id"] for p in liked] == [post_id] == [p["id"] for p in saved]
    assert liked[0]["is_liked"] and liked[0]["is_saved"] and liked[0]["save_count"] == 1

    assert client.delete(f"/posts/{post_id}/save", headers=a).json() == {"saved": False, "save_count": 0}
    assert client.delete(f"/posts/{post_id}/like", headers=a).json() == {"liked": False, "like_count": 0}
    assert client.get("/me/likes", headers=a).json()["items"] == []
    assert client.get("/me/saved", headers=a).json()["items"] == []
    assert client.post("/posts/999/like", headers=a).status_code == 404


def test_comments_replies_and_likes(client):
    a, _ = signup(client, "a@test.com", tier="beginner")
    b, _ = signup(client, "b@test.com", tier="beginner")
    c, _ = signup(client, "c@test.com", tier="beginner")
    post_id = make_post(client, a)["post"]["id"]
    other_post = make_post(client, a)["post"]["id"]

    top = client.post(f"/posts/{post_id}/comments", json={"text": "크림은 얼마나 넣으셨어요?"}, headers=b).json()
    assert top["parent_id"] is None and top["is_mine"] is True
    reply = client.post(f"/posts/{post_id}/comments", json={"text": "200ml요!", "parent_id": top["id"]}, headers=a).json()
    nested = client.post(f"/posts/{post_id}/comments", json={"text": "감사해요", "parent_id": reply["id"]}, headers=b).json()
    assert reply["parent_id"] == top["id"] and nested["parent_id"] == top["id"]  # replies stay one level deep

    wrong_post = client.post(f"/posts/{other_post}/comments", json={"text": "x", "parent_id": top["id"]}, headers=b)
    assert wrong_post.status_code == 404
    assert client.post(f"/posts/{post_id}/comments", json={"text": "   "}, headers=b).status_code == 422

    assert client.post(f"/comments/{top['id']}/like", headers=c).json() == {"liked": True, "like_count": 1}
    assert client.post(f"/comments/{top['id']}/like", headers=c).json()["like_count"] == 1
    listing = client.get(f"/posts/{post_id}/comments", headers=c).json()
    assert listing["total"] == 3 and [x["id"] for x in listing["items"]] == [top["id"], reply["id"], nested["id"]]
    assert listing["items"][0]["is_liked"] is True and listing["items"][1]["is_liked"] is False
    assert client.get(f"/posts/{post_id}", headers=c).json()["comment_count"] == 3
    assert client.delete(f"/comments/{top['id']}/like", headers=c).json() == {"liked": False, "like_count": 0}


# ------------------------------------------------------------------ recipes
def test_recipe_search_filters_and_detail(client):
    h, _ = signup(client, "a@test.com", tier="intermediate")
    rater, _ = signup(client, "b@test.com", tier="beginner")
    rater2, _ = signup(client, "c@test.com", tier="beginner")
    pasta = make_post(client, h, category="pasta")["post"]["id"]
    tuna = make_post(
        client, h, title="참치마요 덮밥", cost_krw=2800, cook_minutes=10, difficulty="beginner", category="rice",
        ingredients=[{"name": "참치캔", "amount": "1개"}, {"name": "밥"}],
    )["post"]["id"]

    def ids(**params):
        return {p["id"] for p in client.get("/recipes", params=params, headers=h).json()["items"]}

    assert ids() == {pasta, tuna}
    assert ids(q="파스타") == {pasta}
    assert ids(q="참치") == {tuna}  # matches ingredient names too
    assert ids(q="%") == set()  # LIKE wildcards are escaped, not interpreted
    assert ids(max_cost=5000) == {pasta, tuna} and ids(max_cost=3000) == {tuna}
    assert ids(category="pasta") == {pasta} and ids(difficulty="beginner") == {tuna}
    assert ids(max_minutes=10) == {tuna}

    client.post(f"/posts/{tuna}/like", headers=rater)
    popular = client.get("/recipes?sort=popular", headers=h).json()["items"]
    assert [p["id"] for p in popular] == [tuna, pasta]

    detail = client.get(f"/recipes/{tuna}", headers=rater).json()
    assert [(i["name"], i["amount"]) for i in detail["ingredients"]] == [("참치캔", "1개"), ("밥", None)]
    assert [(s["order"], s["text"]) for s in detail["steps"]][0] == (1, "파스타를 8분 삶는다")
    assert detail["rating_avg"] is None and detail["rating_count"] == 0 and detail["my_rating"] is None

    assert client.put(f"/recipes/{tuna}/rating", json={"score": 4}, headers=rater).json() == {
        "rating_avg": 4.0, "rating_count": 1, "my_rating": 4,
    }
    assert client.put(f"/recipes/{tuna}/rating", json={"score": 5}, headers=rater2).json()["rating_avg"] == 4.5
    assert client.put(f"/recipes/{tuna}/rating", json={"score": 5}, headers=rater).json()["rating_avg"] == 5.0
    assert client.put(f"/recipes/{tuna}/rating", json={"score": 5}, headers=h).status_code == 400  # own recipe
    assert client.put(f"/recipes/{tuna}/rating", json={"score": 6}, headers=rater).status_code == 422
    assert client.get("/recipes/999", headers=h).status_code == 404


def test_winners_are_last_finished_battle_per_tier(client, freeze):
    freeze(kst_noon(-1))
    h1, _ = signup(client, "a@test.com", tier="intermediate")
    h2, _ = signup(client, "b@test.com", tier="intermediate")
    fan, _ = signup(client, "fan@test.com")
    battle_id = client.get("/battles/today", headers=h1).json()["id"]
    make_post(client, h1, title="첫번째 요리", battle_id=battle_id)
    winner = make_post(client, h2, title="우승 요리", battle_id=battle_id)["post"]["id"]
    client.post(f"/posts/{winner}/like", headers=fan)

    assert client.get("/recipes/winners", headers=fan).json() == []  # yesterday's battle is still open "now"

    freeze(kst_noon())
    result = client.get("/recipes/winners", headers=fan).json()
    assert [(w["tier"], w["tier_label"], w["recipe"]["id"]) for w in result] == [("intermediate", "중급", winner)]
    assert result[0]["recipe"]["recipe"]["title"] == "우승 요리"


# ------------------------------------------------------------------ shop
def test_shop_purchase_and_coupons(client):
    h, me = signup(client, "a@test.com", tier="beginner")
    other, _ = signup(client, "b@test.com")

    shop = client.get("/shop/items", headers=h).json()
    assert shop["coins"] == 0 and shop["available_coupon_count"] == 0
    assert [(i["name"], i["price_coins"]) for i in shop["items"]] == [
        ("커피 쿠폰", 500), ("음식 쿠폰", 800), ("편의점 쿠폰", 300), ("학식 식권", 450),
    ]
    assert [i["name"] for i in client.get("/shop/items?category=cafe", headers=h).json()["items"]] == ["커피 쿠폰"]
    assert client.get("/shop/items?category=food", headers=h).json()["items"][1]["value_krw"] is None
    coffee = shop["items"][0]

    broke = client.post(f"/shop/items/{coffee['id']}/purchase", headers=h)
    assert broke.status_code == 400 and broke.json()["code"] == "insufficient_coins"

    set_user(me["id"], coins=2450)
    bought = client.post(f"/shop/items/{coffee['id']}/purchase", headers=h)
    assert bought.status_code == 201
    coupon = bought.json()["coupon"]
    assert bought.json()["coins"] == 1950  # 2,450 - 500, as in the purchase sheet
    assert len(coupon["code"]) == 12 and coupon["code"].isdigit()
    assert coupon["status"] == "available" and coupon["is_new"] is True and coupon["value_label"] == "₩4,500 상당"
    days = (dt.datetime.fromisoformat(coupon["expires_at"].replace("Z", "+00:00")) - dt.datetime.now(dt.timezone.utc)).days
    assert 88 <= days <= 90
    assert client.post("/shop/items/999/purchase", headers=h).status_code == 404

    listing = client.get("/me/coupons", headers=h).json()
    assert (listing["available_count"], listing["used_count"]) == (1, 0) and len(listing["items"]) == 1
    assert client.get("/shop/items", headers=h).json()["available_coupon_count"] == 1

    assert client.post(f"/me/coupons/{coupon['id']}/use", headers=other).status_code == 404  # not theirs
    used = client.post(f"/me/coupons/{coupon['id']}/use", headers=h)
    assert used.status_code == 200 and used.json()["status"] == "used"
    again = client.post(f"/me/coupons/{coupon['id']}/use", headers=h)
    assert again.status_code == 409 and again.json()["code"] == "coupon_already_used"

    assert client.get("/me/coupons", headers=h).json()["items"] == []
    after = client.get("/me/coupons?status=used", headers=h).json()
    assert (after["available_count"], after["used_count"], len(after["items"])) == (0, 1, 1)

    with SessionLocal() as db:
        rows = db.scalars(select(LedgerEntry).where(LedgerEntry.user_id == me["id"], LedgerEntry.reason == "purchase")).all()
        assert [r.coin_delta for r in rows] == [-500]


def test_purchase_spends_exactly_and_never_goes_negative(client):
    h, me = signup(client, "a@test.com")
    set_user(me["id"], coins=500)
    coffee = client.get("/shop/items", headers=h).json()["items"][0]["id"]
    assert client.post(f"/shop/items/{coffee}/purchase", headers=h).json()["coins"] == 0
    assert client.post(f"/shop/items/{coffee}/purchase", headers=h).status_code == 400
    assert client.get("/me", headers=h).json()["coins"] == 0
    assert len(client.get("/me/coupons?status=all", headers=h).json()["items"]) == 1


def test_expired_coupon_cannot_be_used(client, freeze):
    h, me = signup(client, "a@test.com")
    set_user(me["id"], coins=500)
    coffee = client.get("/shop/items", headers=h).json()["items"][0]["id"]
    coupon = client.post(f"/shop/items/{coffee}/purchase", headers=h).json()["coupon"]

    freeze(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=91))
    assert client.get("/me/coupons", headers=h).json()["available_count"] == 0
    expired = client.get("/me/coupons?status=expired", headers=h).json()
    assert expired["expired_count"] == 1 and expired["items"][0]["status"] == "expired"
    late = client.post(f"/me/coupons/{coupon['id']}/use", headers=h)
    assert late.status_code == 410 and late.json()["code"] == "coupon_expired"


def test_ledger_records_every_change(client):
    h, me = signup(client, "a@test.com", tier="beginner")
    make_post(client, h)
    with SessionLocal() as db:
        user = db.get(User, me["id"])
        entries = db.scalars(select(LedgerEntry).where(LedgerEntry.user_id == me["id"])).all()
        assert (user.xp, user.coins) == (sum(e.xp_delta for e in entries), sum(e.coin_delta for e in entries)) == (50, 30)
