"""전체 흐름 스모크 테스트 (임시 DB 사용, 실제 데이터 영향 없음).

실행 (backend 폴더, 가상환경 켠 상태):
    pip install httpx
    python -m tests.smoke_test
"""
import datetime as dt
import io
import os
import random
import tempfile

tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{tmp}/uploads"
os.environ["ADMIN_EMAILS"] = "admin@test.com"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app import seed  # noqa: E402
from app.main import app  # noqa: E402

seed.run()
c = TestClient(app)
step = 0

_web = c.get("/")
assert _web.status_code == 200 and "요리왕" in _web.text, "웹앱(/)이 열리지 않아요"
assert c.get("/app.js").status_code == 200 and c.get("/health").json() == {"status": "ok"}, "웹앱 파일/헬스 체크"


def check(cond, msg):
    global step
    step += 1
    assert cond, f"[{step}] {msg}"


def ok(r, code=200):
    assert r.status_code == code, f"기대 {code}, 실제 {r.status_code}: {r.text}"
    return r.json()


_seed = [0]


def scene():
    """매번 다른 사진 (랜덤 도형)."""
    _seed[0] += 1
    r = random.Random(_seed[0])
    im = Image.new("RGB", (640, 480), (r.randint(90, 200),) * 3)
    d = ImageDraw.Draw(im)
    for _ in range(12):
        x, y = r.randint(0, 640), r.randint(0, 480)
        d.rectangle([x, y, x + r.randint(40, 300), y + r.randint(40, 300)],
                    fill=tuple(r.randint(0, 255) for _ in range(3)))
    return im


def as_file(im, exif=None):
    buf = io.BytesIO()
    if exif is not None:
        im.save(buf, "JPEG", exif=exif)
    else:
        im.save(buf, "JPEG")
    buf.seek(0)
    return ("food.jpg", buf, "image/jpeg")


def img(color=None):
    return as_file(scene())


def guide(H, battle_id):
    return [x["shot_type"] for x in ok(c.get(f"/battles/{battle_id}/shot-guide", headers=H))["shots"]]


EMAILS = {"지원": "jiwon@test.com", "민준": "minjun@test.com", "서연": "seoyeon@test.com", "고수": "gosu@test.com"}


def signup(nick, skill="low", invite=None, email=None):
    body = {"email": email or EMAILS[nick], "nickname": nick, "password": "pass1234", "skill": skill}
    if invite:
        body["invite_code"] = invite
    d = ok(c.post("/auth/signup", json=body))
    return {"Authorization": f"Bearer {d['access_token']}"}, d["user"]


def submit(H, battle_id, title, cost=None, shots=None, files=None):
    """촬영 가이드대로 구도마다 다른 사진을 올린다 (shots/files로 덮어쓰기 가능)."""
    shots = shots if shots is not None else guide(H, battle_id)
    files = files if files is not None else [img() for _ in shots]
    data = {"title": title, "shots": shots}
    if cost is not None:
        data["ingredient_cost"] = str(cost)
    return c.post(f"/battles/{battle_id}/submissions", headers=H, data=data,
                  files=[("files", f) for f in files])


# ---------- 가입 / 로그인 ----------
A, admin = signup("관리자", email="admin@test.com")
check(admin["is_admin"], "관리자 이메일이면 관리자")
H1, u1 = signup("지원")
H2, _ = signup("민준", invite=u1["invite_code"])
H3, _ = signup("서연", invite=u1["invite_code"])
H4, u4 = signup("고수", skill="high")
check(u4["skill_label"] == "상", "실력 라벨")
def raw_signup(email, nick, skill="low"):
    return c.post("/auth/signup", json={"email": email, "nickname": nick, "password": "pass1234", "skill": skill})


check(raw_signup("new@test.com", "지원").json().get("detail") == "이미 사용 중인 닉네임입니다", "닉네임 중복")
check(raw_signup("jiwon@test.com", "새사람").json().get("detail") == "이미 가입된 이메일입니다", "이메일 중복")
check(raw_signup("x@test.com", "새사람", skill="x").status_code == 400, "실력 미선택")
check(raw_signup("not-an-email", "새사람2").status_code == 422, "이메일 형식")
check(ok(c.get("/auth/check-nickname", params={"nickname": "지원"}))["available"] is False, "닉네임 중복 확인")
check(ok(c.get("/auth/check-nickname", params={"nickname": "새사람"}))["available"] is True, "사용 가능 닉네임")
check(ok(c.get("/auth/check-email", params={"email": "jiwon@test.com"}))["available"] is False, "이메일 중복 확인")
check(ok(c.post("/auth/login", json={"email": "jiwon@test.com", "password": "pass1234"}))["user"]["id"] == u1["id"],
      "이메일 로그인")
check(c.post("/auth/login", json={"email": "jiwon@test.com", "password": "wrong"}).status_code == 401, "비밀번호 오류")
check(ok(c.post("/auth/token", data={"username": "jiwon@test.com", "password": "pass1234"}))["access_token"],
      "Swagger 로그인")

# ---------- 보안 ----------
check(raw_signup("fake@test.com", "관리자2").json()["detail"] == "사용할 수 없는 닉네임이에요", "운영진 사칭 닉네임 차단")
check(raw_signup("fake2@test.com", "<script>").status_code == 400, "닉네임 특수문자 차단")
weak = c.post("/auth/signup", json={"email": "w@test.com", "nickname": "약한비번", "password": "12345678", "skill": "low"})
check(weak.status_code == 422 and isinstance(weak.json()["detail"], str) and "영문과 숫자" in weak.json()["detail"],
      "약한 비밀번호 거절 + 422도 한 줄 메시지")
nick = ok(c.get("/auth/check-nickname", params={"nickname": "운영자"}))
check(nick["available"] is False and nick["reason"], "닉네임 확인에 이유 표시")
check(c.get("/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401, "위조 토큰 거절")
check(c.get("/users/me").status_code == 401, "토큰 없으면 401")
check(c.get("/battles/history", params={"limit": -1}, headers=H1).status_code == 422, "음수 limit 거절")
tmp_h, _ = signup("임시계정", email="temp@test.com")
ok(c.post("/auth/logout-all", headers=tmp_h))
check(c.get("/users/me", headers=tmp_h).status_code == 401, "전체 로그아웃 → 기존 토큰 무효")
for _ in range(10):
    c.post("/auth/login", json={"email": "temp@test.com", "password": "wrong1234"})
check(c.post("/auth/login", json={"email": "temp@test.com", "password": "pass1234"}).status_code == 429,
      "로그인 10회 실패 → 잠시 잠금")
check(ok(c.get("/users/me", headers=H1))["total_points"] == 4, "초대 2명 × 2P")

# ---------- 대결 ----------
b = ok(c.get("/battles/current", headers=H1))
check(b["group"] == "low" and b["days_left"] == 6 and b["category"]["name"], "하 그룹 대결 자동 생성")
check(b["phase"] == "cooking" and b["phase_days_left"] == 4 and b["can_submit"], "요리 기간 5일로 시작")
check(b["cooking_end_date"] < b["vote_start_date"] <= b["end_date"], "요리 5일 → 투표 2일")
bid = b["id"]
check(ok(c.get("/battles/current", headers=H2))["id"] == bid, "같은 그룹은 같은 대결")
bh = ok(c.get("/battles/current", headers=H4))
check(bh["id"] != bid and bh["group"] == "high", "상 그룹은 별도 대결")
check(len(ok(c.get("/battles/active", headers=H1))) == 4, "리그 3개 + 망한 요리 대회")

check(submit(H4, bid, "남의 그룹").status_code == 403, "다른 그룹 대결 참가 불가")

# ---------- 다중 구도 인증샷 ----------
g1 = ok(c.get(f"/battles/{bid}/shot-guide", headers=H1))
shots1 = [x["shot_type"] for x in g1["shots"]]
check(len(shots1) == 3 and shots1[0] == "front" and shots1[-1] == "keyword", "촬영 가이드: 정면 + 랜덤 + 키워드")
check(guide(H1, bid) == shots1, "가이드는 새로고침해도 같음")
others = {tuple(guide(H, bid)) for H in (H2, H3, A)} | {tuple(shots1)}
print("   (사용자별 랜덤 구도 조합:", sorted({s[1] for s in others}), ")")


def detail(r):
    return r.json().get("detail", "")


r = submit(H1, bid, "x", shots=shots1[:2], files=[img(), img()])
check(r.status_code == 400 and "빠졌어요" in detail(r), "구도 누락 거절")
r = submit(H1, bid, "x", shots=[shots1[0], shots1[0], shots1[2]])
check(r.status_code == 400 and "두 번" in detail(r), "같은 구도 중복 거절")
wrong = next(k for k in ("top", "side", "closeup", "process") if k not in shots1)
r = submit(H1, bid, "x", shots=[shots1[0], wrong, shots1[2]])
check(r.status_code == 400 and "필요 없는 구도" in detail(r), "요구되지 않은 구도 거절")
same = scene()
r = submit(H1, bid, "x", files=[as_file(same), as_file(same.resize((600, 450))), img()])
check(r.status_code == 400 and "같은 사진" in detail(r), "같은 사진을 여러 구도로 올리면 거절")
r = submit(H1, bid, "x", files=[img(), ("a.jpg", io.BytesIO(b"nope"), "image/jpeg"), img()])
check(r.status_code == 400 and "이미지 파일이 아닙니다" in detail(r), "이미지 아닌 파일 거절")
small = scene().resize((200, 150))
r = submit(H1, bid, "x", files=[img(), as_file(small), img()])
check(r.status_code == 400 and "너무 작아요" in detail(r), "저해상도 거절")
r = submit(H1, bid, "x", files=[img(), img(), as_file(Image.new("RGB", (640, 480), (3, 3, 3)))])
check(r.status_code == 400 and "어두워요" in detail(r), "너무 어두운 사진 거절")
old_exif = Image.Exif()
old_exif[306] = "2020:01:01 12:00:00"
r = submit(H1, bid, "x", files=[img(), as_file(scene(), exif=old_exif), img()])
check(r.status_code == 400 and "대결 기간이 아닐 때" in detail(r), "옛날에 찍은 사진 거절 (EXIF)")

now_exif = Image.Exif()
now_exif[306] = dt.datetime.now().strftime("%Y:%m:%d %H:%M:%S")
reused = scene()
r1 = ok(submit(H1, bid, "계란말이", cost=2000,
               files=[as_file(reused, exif=now_exif), as_file(scene(), exif=now_exif), as_file(scene(), exif=now_exif)]))
check(r1["points_earned"] == 1 and r1["submission"]["title"] == "계란말이", "참가 즉시 +1P")
imgs = r1["submission"]["images"]
check([i["shot_type"] for i in imgs] == shots1 and imgs[0]["shot_label"], "구도별 사진 저장")
check(r1["submission"]["photo_verified"], "촬영 시각 확인 → 촬영 인증 배지")
check(r1["submission"]["image_url"].endswith(".jpg"), "JPEG로 재저장")
check(submit(H1, bid, "또").status_code == 400, "중복 참가")
s1 = r1["submission"]["id"]
r = submit(H2, bid, "스크램블", files=[as_file(reused.resize((500, 375))), img(), img()])
check(r.status_code == 400 and "이미 올라온 적 있는" in detail(r), "남이 올린 사진 재사용 거절")
r2 = ok(submit(H2, bid, "스크램블", cost=3000))
check(not r2["submission"]["photo_verified"], "EXIF 없으면 미인증 (참가는 가능)")
s2 = r2["submission"]["id"]
s3 = ok(submit(H3, bid, "계란찜"))["submission"]["id"]
s4 = ok(submit(A, bid, "관리자 요리"))["submission"]["id"]

# ---------- 투표 (투표 기간에만, 그 대결 참가자만) ----------
r = c.post(f"/submissions/{s1}/vote", headers=H2)
check(r.status_code == 400 and "요리 기간" in detail(r), "요리 기간엔 투표 불가")
check(not ok(c.get(f"/battles/{bid}", headers=H2))["can_vote"], "요리 기간 can_vote=false")
check(c.post(f"/admin/battles/{bid}/phase", headers=H1, json={"phase": "voting"}).status_code == 403,
      "기간 전환은 관리자만")
vb = ok(c.post(f"/admin/battles/{bid}/phase", headers=A, json={"phase": "voting"}))
check(vb["phase"] == "voting" and vb["phase_label"] == "투표 기간" and not vb["can_submit"], "투표 기간으로 전환")
H7, _ = signup("늦은참가", email="late@test.com")
r = submit(H7, bid, "늦은 요리")
check(r.status_code == 400 and "투표 기간" in detail(r), "투표 기간엔 참가 불가")
r = c.post(f"/submissions/{s1}/vote", headers=H7)
check(r.status_code == 403 and "참가한 사람만" in detail(r), "참가 안 한 사람은 투표 불가")
check(c.post(f"/submissions/{s1}/vote", headers=H4).status_code == 403, "다른 리그 사람도 투표 불가")
check("참가한 사람만" in ok(c.get(f"/battles/{bid}", headers=H7))["vote_block_reason"], "투표 불가 이유 표시")
check(c.post(f"/submissions/{s1}/vote", headers=H1).status_code == 400, "내 작품 투표 불가")
check(ok(c.get(f"/battles/{bid}", headers=H2))["can_vote"], "참가자는 can_vote=true")
check(ok(c.post(f"/submissions/{s1}/vote", headers=H2))["vote_count"] == 1, "투표 + 투표 수")
check(c.post(f"/submissions/{s3}/vote", headers=H2).status_code == 400, "1인 1표")
ok(c.post(f"/submissions/{s1}/vote", headers=H3))
ok(c.post(f"/submissions/{s2}/vote", headers=H1))
ok(c.post(f"/submissions/{s3}/vote", headers=A))
lst = ok(c.get(f"/battles/{bid}/submissions", headers=H2))
check(len(lst) == 4 and any(s["has_voted"] for s in lst), "출품작 목록 + 내 투표 표시")
check(ok(c.get(f"/battles/{bid}", headers=H2))["has_voted"], "대결 has_voted")

# ---------- 작품 평가 (댓글 + 별점) ----------
cm = ok(c.post(f"/submissions/{s1}/comments", headers=H2, json={"content": "맛있어 보여요", "rating": 5}))
check(cm["nickname"] == "민준" and cm["rating"] == 5 and cm["created_at_display"], "평가: 닉네임·별점·시간")
ok(c.post(f"/submissions/{s1}/comments", headers=H3, json={"content": "간이 좀 셀 듯", "rating": 2}))
check(c.post(f"/submissions/{s1}/comments", headers=H1, json={"content": "셀프", "rating": 5}).status_code == 400,
      "내 작품 평가 불가")
check(c.post(f"/submissions/{s1}/comments", headers=H2, json={"content": "또", "rating": 4}).status_code == 400,
      "작품당 평가 1번")
check(c.post(f"/submissions/{s2}/comments", headers=H1, json={"content": "x", "rating": 6}).status_code == 422,
      "별점 범위 1~5")
lst_c = ok(c.get(f"/submissions/{s1}/comments", headers=H1))
check(lst_c["summary"]["average"] == 3.5 and lst_c["summary"]["count"] == 2, "별점 평균")
check(lst_c["summary"]["distribution"]["5"] == 1, "별점 분포")
check(ok(c.get(f"/submissions/{s1}/comments", headers=H1, params={"sort": "rating_low"}))["comments"][0]["rating"] == 2,
      "별점 낮은순")
ed = ok(c.patch(f"/comments/{cm['id']}", headers=H2, json={"rating": 4}))
check(ed["rating"] == 4 and ed["is_edited"], "평가 수정")
check(c.patch(f"/comments/{cm['id']}", headers=H3, json={"rating": 1}).status_code == 403, "남의 평가 수정 불가")
check(ok(c.get(f"/submissions/{s1}/comments/mine", headers=H2))["id"] == cm["id"], "내 평가 조회")
check(ok(c.get(f"/submissions/{s1}", headers=H1))["rating_avg"] == 3.0, "작품 객체에 평균 별점")

# ---------- 마감 / 결과 ----------
check(c.get(f"/battles/{bid}/results", headers=H1).status_code == 400, "마감 전 결과 불가")
check(c.post(f"/admin/battles/{bid}/close", headers=H1).status_code == 403, "관리자만 종료")
ok(c.post(f"/admin/battles/{bid}/close", headers=A))
check(c.post(f"/submissions/{s2}/vote", headers=H4).status_code == 400, "종료 후 투표 불가")

res = ok(c.get(f"/battles/{bid}/results", headers=H1))
check([e["submission_id"] for e in res["podium"]] == [s1, s2, s3], "시상대 순서")
check([e["rank_points"] for e in res["podium"]] == [5, 4, 3], "1/2/3등 5/4/3P")
my = res["my_result"]
check(my["rank"] == 1 and my["points_earned"] == 6 and my["can_share_recipe"], "내 결과")
check(my["leveled_up"] and my["level_before"] == 1 and my["level_after"] == 2, "레벨업 팝업 정보 (4+1+5=10P)")
me1 = ok(c.get("/users/me", headers=H1))
check(me1["level"] == 2 and me1["points"] == 10 and me1["level_progress"] == 0.0, "레벨 2")

# ---------- 새 대결 / 무효 대결 ----------
b2 = ok(c.get("/battles/current", headers=H1))
check(b2["id"] != bid and b2["category"]["id"] != b["category"]["id"], "종료 후 새 랜덤 카테고리 대결")
ok(submit(H1, b2["id"], "라면", cost=1500))
ok(c.post(f"/admin/battles/{b2['id']}/close", headers=A))
res2 = ok(c.get(f"/battles/{b2['id']}/results", headers=H1))
check(res2["is_void"] and res2["podium"] == [] and not res2["my_result"]["can_share_recipe"], "3명 미만 무효")
check(res2["my_result"]["points_earned"] == 1, "무효여도 참가 포인트")

# ---------- 홈 ----------
home = ok(c.get("/users/me/home", headers=H1))
check(home["this_month"]["cook_count"] == 2, "이번 달 요리 횟수")
check(home["this_month"]["saved_money"] == (15000 - 2000) + (15000 - 1500), "절약 식비")
check(home["history"][-1]["rank"] == 1, "참가 이력 순위")

# ---------- 레시피 ----------
body = {"title": "폭신 계란말이", "ingredients": [{"name": "계란", "amount": "3개", "price": 900},
                                                  {"name": "대파", "amount": "약간", "price": 300}, {"name": "소금"}],
        "steps": ["풀고", "말고"], "cook_minutes": 10, "difficulty": "easy", "food_type": "side", "tags": ["자취 필수"]}
check(c.post(f"/submissions/{s2}/recipe", headers=H2, json=body).status_code == 403, "우승자만 공유")
rec = ok(c.post(f"/submissions/{s1}/recipe", headers=H1, json=body))
check(rec["estimated_cost"] == 1200 and rec["image_url"], "재료비 자동 계산 + 대결 사진")
check(rec["source"] == "winner" and rec["badge"].endswith("대결 1등") and rec["ingredients"][0]["amount"] == "3개",
      "우승 배지 + 재료 분량")
check(ok(c.get(f"/battles/{bid}/results", headers=H2))["entries"][0]["recipe_id"] == rec["id"], "결과 TOP에 '레시피 공유' 연결")
check(c.post(f"/submissions/{s1}/recipe", headers=H1, json=body).status_code == 400, "중복 공유")
ok(c.post(f"/recipes/{rec['id']}/image", headers=H1, files={"file": img("blue")}))
check(c.post(f"/recipes/{rec['id']}/image", headers=H2, files={"file": img()}).status_code == 403, "작성자만 사진 변경")

check(ok(c.post(f"/recipes/{rec['id']}/save", headers=H2))["saved_by_me"], "레시피 저장")
ok(c.post(f"/recipes/{rec['id']}/save", headers=H3))
check(ok(c.get("/recipes", params={"sort": "popular"}, headers=H2))["items"][0]["id"] == rec["id"], "인기순")
check(len(ok(c.get("/users/me/saved-recipes", headers=H2))) == 1, "저장한 레시피")
ok(c.delete(f"/recipes/{rec['id']}/save", headers=H3))
ok(c.get(f"/recipes/{rec['id']}", headers=H2))
check(ok(c.get("/users/me/recent-recipes", headers=H2))[0]["id"] == rec["id"], "최근 본 레시피")
rv = ok(c.post(f"/recipes/{rec['id']}/reviews", headers=H2, json={"content": "따라해 봤는데 맛있어요"}))
check(len(ok(c.get("/reviews", headers=H3))) == 1, "후기 모음")
check(len(ok(c.get("/users/me/home", headers=H2))["my_reviews"]) == 1, "홈 > 내가 쓴 후기")
check(c.delete(f"/reviews/{rv['id']}", headers=H3).status_code == 403, "남의 후기 삭제 불가")
ok(c.post(f"/recipes/{rec['id']}/complete", headers=H3, files={"file": img()}))
check(c.post(f"/recipes/{rec['id']}/complete", headers=H3, files={"file": img()}).status_code == 400, "완료 1회")

# ---------- 레시피 목록·필터 (디자인 04/05) ----------
opts = ok(c.get("/recipes/options"))
check(len(opts["food_types"]) == 8 and len(opts["quick_filters"]) == 5 and opts["budgets"][0]["params"] == {"max_cost": 5000},
      "필터 선택지")
allr = ok(c.get("/recipes", params={"limit": 100}, headers=H1))
check(allr["total"] == 11 and allr["items"][0]["created_at"] >= allr["items"][-1]["created_at"], "전체 목록(공식 10 + 우승 1), 최신순")


def rl(**params):
    return ok(c.get("/recipes", params={"limit": 100, **params}, headers=H1))


cheap = rl(max_cost=5000)
check(cheap["total"] and all(r["estimated_cost"] is not None and r["estimated_cost"] <= 5000 for r in cheap["items"]),
      "예산 5,000원 이하")
mid = rl(min_cost=5000, max_cost=10000)
check(all(5000 <= r["estimated_cost"] <= 10000 for r in mid["items"]) and mid["total"] >= 2, "예산 5,000~10,000원")
check([r["title"] for r in rl(min_minutes=60)["items"]] == ["찹스테이크"], "조리 1시간 이상")
quick_easy = rl(max_minutes=15, difficulty="easy")
check(all(r["cook_minutes"] <= 15 and r["difficulty_label"] == "초급" for r in quick_easy["items"]), "15분 이내 + 초급")
check(all("자취 필수" in r["tags"] for r in rl(tag="자취 필수")["items"]), "태그: 자취 필수")
check({r["food_type_label"] for r in rl(type="rice,noodle")["items"]} == {"밥", "면"}, "종류 여러 개 (밥, 면)")
check([r["title"] for r in rl(q="베이컨")["items"]] == ["크림 파스타"], "검색: 재료 이름으로")
fr_ = rl(have="계란,김치,밥")
check(fr_["items"][0]["title"] == "김치볶음밥" and fr_["items"][0]["missing_ingredients"] == ["식용유"],
      "재료로 찾기: 부족한 재료 적은 순")
cheap_sorted = [r["estimated_cost"] for r in rl(sort="cheap")["items"] if r["estimated_cost"] is not None]
check(cheap_sorted == sorted(cheap_sorted), "저렴한순")
check(ok(c.get("/recipes/count", params={"max_cost": 5000}, headers=H1))["total"] == cheap["total"], "필터 결과 개수")
check(len(rl(limit=3)["items"]) == 3 and rl(limit=3)["total"] == 11, "페이지 나누기 (total은 전체)")
check(c.get("/recipes", params={"sort": "weird"}, headers=H1).status_code == 422, "잘못된 정렬 값")

# ---------- 레시피 올리기 / 수정 / 삭제 ----------
new_body = {"title": "라면 볶이", "ingredients": [{"name": "라면", "amount": "1봉", "price": 1000},
                                                {"name": "떡", "amount": "한 줌", "price": 800}],
            "steps": ["라면을 삶는다", "양념에 볶는다"], "cook_minutes": 12, "difficulty": "easy",
            "food_type": "noodle", "tags": ["야식"]}
check(c.post("/recipes", headers=H3, json={**new_body, "difficulty": "super"}).status_code == 422, "잘못된 난이도 거절")
check(c.post("/recipes", headers=H3, json={**new_body, "tags": ["아무태그"]}).status_code == 422, "정해진 태그만")
check(c.post("/recipes", headers=H3, params={"official": "true"}, json=new_body).status_code == 403, "공식 레시피는 관리자만")
mine_r = ok(c.post("/recipes", headers=H3, json=new_body))
check(mine_r["source"] == "user" and mine_r["badge"] is None and mine_r["is_mine"] and mine_r["estimated_cost"] == 1800,
      "누구나 레시피 올리기")
ok(c.post(f"/recipes/{mine_r['id']}/image", headers=H3, files={"file": img()}))
check(c.patch(f"/recipes/{mine_r['id']}", headers=H2, json={"cook_minutes": 5}).status_code == 403, "남의 레시피 수정 불가")
ed = ok(c.patch(f"/recipes/{mine_r['id']}", headers=H3,
                json={"cook_minutes": 8, "ingredients": [{"name": "라면", "amount": "1봉", "price": 1200}]}))
check(ed["cook_minutes"] == 8 and ed["estimated_cost"] == 1200, "레시피 수정 (재료비 재계산)")
check(len(ok(c.get("/users/me/recipes", headers=H3))) == 1, "내가 올린 레시피")
check(rl(source="user")["total"] == 1, "출처 필터: 사용자 레시피")
ok(c.delete(f"/recipes/{mine_r['id']}", headers=H3))
check(c.get(f"/recipes/{mine_r['id']}", headers=H3).status_code == 404, "레시피 삭제")

# ---------- 상점 ----------
items = ok(c.get("/shop/items", headers=H1))
cheap = next(i for i in items if i["price"] == 10)
lvl = next(i for i in items if i["min_level"] == 3)
check(cheap["can_exchange"], "교환 가능")
check(lvl["blocked_reason"] == "3레벨부터 교환 가능", "레벨 제한")
ex = ok(c.post(f"/shop/items/{cheap['id']}/exchange", headers=H1))
check(ex["points_left"] == 1, "보유 포인트 차감 (11-10)")
me1 = ok(c.get("/users/me", headers=H1))
check(me1["total_points"] == 11 and me1["level"] == 2, "누적 포인트·레벨은 유지")
again = c.post(f"/shop/items/{cheap['id']}/exchange", headers=H1)
check(again.status_code == 400 and "포인트 더 필요" in again.json()["detail"], "포인트 부족")
check(len(ok(c.get("/users/me/exchanges", headers=H1))) == 1, "교환 내역")

# ---------- 튜토리얼 / 설정 ----------
check(ok(c.patch("/users/me/tutorial", headers=H1, json={"step": 2}))["tutorial_step"] == 2, "튜토리얼 이어보기")
check(ok(c.patch("/users/me/tutorial", headers=H1, json={"completed": True}))["tutorial_completed"], "튜토리얼 완료")
check(c.patch("/users/me", headers=H1, json={"nickname": "민준"}).status_code == 400, "닉네임 변경 중복")
check(ok(c.patch("/users/me", headers=H1, json={"notifications_enabled": False}))["user"]["notifications_enabled"]
      is False, "알림 설정")
check(c.patch("/users/me", headers=H1, json={"current_password": "x", "new_password": "newpass123"}).status_code == 400,
      "비밀번호 변경은 현재 비밀번호 필요")
pw = ok(c.patch("/users/me", headers=H3, json={"current_password": "pass1234", "new_password": "newpass123"}))
check(c.get("/users/me", headers=H3).status_code == 401 and pw["access_token"], "비밀번호 변경 → 이전 토큰 무효")
H3 = {"Authorization": f"Bearer {pw['access_token']}"}
check(ok(c.get("/users/me", headers=H3))["nickname"] == "서연", "새 토큰으로 계속 사용")

# ---------- 신고 ----------
b3 = ok(c.get("/battles/current", headers=H2))
s = ok(submit(H2, b3["id"], "야식"))["submission"]["id"]
for H in (H1, H3, H4):
    r = ok(c.post(f"/submissions/{s}/report", headers=H, json={"reason": "퍼온 사진"}))
check(r["is_hidden"] and ok(c.get(f"/battles/{b3['id']}/submissions", headers=H1)) == [], "신고 누적 숨김")

check("skills" in ok(c.get("/meta")), "메타")

# ---------- 이미지 인식 AI (가짜 응답으로 판정 흐름 확인, 실제 API 호출 없음) ----------
from app.config import settings  # noqa: E402
from app.services import ai_vision  # noqa: E402

check(ok(c.get("/meta"))["ai_check"]["enabled"] is False, "키 없으면 AI 꺼짐")
check(r1["submission"]["ai_check"]["status"] == "skipped", "키 없을 때 참가는 AI 건너뜀")

real_call = ai_vision._call_claude
settings.anthropic_api_key = "test-key"
settings.ai_check_mode = "strict"


def fake_ok(content):
    n = sum(1 for b in content if b["type"] == "image")
    return {"photos": [{"index": i + 1, "is_food": True, "detected_angle": "front", "angle_matches": True,
                        "keyword_visible": True, "confidence": 0.9, "note": "잘 찍었어요"} for i in range(n)],
            "same_dish": True, "category_match": True, "looks_fake": False, "summary": "모든 사진 확인 완료"}


def fake_bad(content):
    r = fake_ok(content)
    r["photos"][-1]["keyword_visible"] = False
    r["photos"][0].update(angle_matches=False, detected_angle="side", confidence=0.95)
    r["same_dish"] = False
    return r


def fake_error(content):
    raise TimeoutError("api down")


try:
    check(ok(c.get("/admin/ai/status", headers=A))["enabled"], "AI 켜짐 (관리자 상태 확인)")
    shots4 = guide(H4, bh["id"])
    ai_vision._call_claude = fake_bad
    pc = ok(c.post(f"/battles/{bh['id']}/shot-check", headers=H4, data={"shot": "keyword"}, files={"file": img()}))
    check(not pc["ok"] and any("메모" in p for p in pc["problems"]), "미리 검사: 키워드 메모 없음")
    r = submit(H4, bh["id"], "고수 요리")
    check(r.status_code == 400 and "AI 사진 검사" in detail(r) and "구도와 달라요" in detail(r), "strict: AI 문제 시 거절")
    check("서로 다른 요리" in detail(r), "strict: 다른 요리 사진 거절")

    ai_vision._call_claude = fake_ok
    pc = ok(c.post(f"/battles/{bh['id']}/shot-check", headers=H4, data={"shot": shots4[1]}, files={"file": img()}))
    check(pc["ok"] and pc["ai_status"] == "passed", "미리 검사 통과")
    ra = ok(submit(H4, bh["id"], "고수 요리"))["submission"]
    check(ra["ai_verified"] and ra["ai_check"]["status"] == "passed", "AI 인증 배지")

    H5, _ = signup("고수2", skill="high", email="gosu2@test.com")
    settings.ai_check_mode = "advisory"
    ai_vision._call_claude = fake_bad
    rb = ok(submit(H5, bh["id"], "고수2 요리"))["submission"]
    check(not rb["ai_verified"] and rb["ai_check"]["warnings"], "advisory: 거절 없이 경고만 기록")

    H6, _ = signup("고수3", skill="high", email="gosu3@test.com")
    settings.ai_check_mode = "strict"
    ai_vision._call_claude = fake_error
    rc = ok(submit(H6, bh["id"], "고수3 요리"))["submission"]
    check(rc["ai_check"]["status"] == "error", "AI 장애 시 참가는 허용 (status=error)")
finally:
    ai_vision._call_claude = real_call
    settings.anthropic_api_key = ""
    settings.ai_check_mode = "strict"
# ---------- 친구 ----------
names = {f["nickname"] for f in ok(c.get("/friends", headers=H2))}
check(names == {"지원"}, "초대 코드로 가입하면 자동 친구")
check({f["nickname"] for f in ok(c.get("/friends", headers=H1))} == {"민준", "서연"}, "초대한 사람 쪽 친구 목록")

found = ok(c.get("/users/search", params={"nickname": "고수"}, headers=H1))
check({u["nickname"] for u in found} >= {"고수", "고수2", "고수3"} and all(u["relation"] == "none" for u in found),
      "닉네임 검색 + 관계 표시")
check(ok(c.get("/users/search", params={"nickname": "민준"}, headers=H1))[0]["relation"] == "friend", "검색: 이미 친구")

req = ok(c.post("/friends/requests", headers=H1, json={"nickname": "고수"}))
check(req["status"] == "pending", "친구 요청 보내기")
check(c.post("/friends/requests", headers=H1, json={"nickname": "고수"}).status_code == 400, "중복 요청 불가")
check(c.post("/friends/requests", headers=H1, json={"nickname": "지원"}).status_code == 400, "나 자신에게 요청 불가")
check(c.post("/friends/requests", headers=H1, json={"nickname": "민준"}).status_code == 400, "이미 친구에게 요청 불가")
check(c.post("/friends/requests", headers=H1, json={"nickname": "없는사람"}).status_code == 404, "없는 닉네임")
check(len(ok(c.get("/friends/requests", params={"box": "sent"}, headers=H1))) == 1, "보낸 요청 목록")
recv = ok(c.get("/friends/requests", headers=H4))
check(len(recv) == 1 and recv[0]["from_user"]["nickname"] == "지원" and recv[0]["created_at_display"], "받은 요청 목록")
check(ok(c.get("/users/search", params={"nickname": "지원"}, headers=H4))[0]["relation"] == "request_received",
      "검색: 받은 요청 표시")
check(c.post(f"/friends/requests/{req['request_id']}/accept", headers=H1).status_code == 403, "보낸 사람은 수락 불가")
ok(c.post(f"/friends/requests/{req['request_id']}/accept", headers=H4))
check("고수" in {f["nickname"] for f in ok(c.get("/friends", headers=H1))}, "수락 → 양쪽 친구")

ok(c.post("/friends/requests", headers=A, json={"nickname": "지원"}))
both = ok(c.post("/friends/requests", headers=H1, json={"nickname": "관리자"}))
check(both["status"] == "accepted", "서로 요청하면 바로 친구")

rq = ok(c.post("/friends/requests", headers=H3, json={"nickname": "고수2"}))
ok(c.post(f"/friends/requests/{rq['request_id']}/reject", headers=H5))
check(ok(c.get("/users/search", params={"nickname": "고수2"}, headers=H3))[0]["relation"] == "none", "거절 → 관계 없음")
rq = ok(c.post("/friends/requests", headers=H3, json={"nickname": "고수3"}))
ok(c.delete(f"/friends/requests/{rq['request_id']}", headers=H3))
check(ok(c.get("/friends/requests", headers=H6)) == [], "요청 취소")

rank = ok(c.get("/friends/ranking", headers=H1))
pts = [r["total_points"] for r in rank]
check(pts == sorted(pts, reverse=True) and any(r["is_me"] for r in rank) and len(rank) == 5, "친구 랭킹 (나 포함)")
check(next(r for r in rank if r["is_me"])["win_count"] == 1, "랭킹에 우승 횟수")
feed = ok(c.get("/friends/activity", headers=H1))
check(feed and all(f["user"]["nickname"] != "지원" for f in feed) and "참가했어요" in feed[0]["message"], "친구 활동 피드")

prof = ok(c.get(f"/users/{u4['id']}/profile", headers=H1))
check(prof["relation"] == "friend" and prof["battle_count"] == 1 and prof["recent_submissions"], "공개 프로필")
ok(c.delete(f"/friends/{u4['id']}", headers=H1))
check(ok(c.get(f"/users/{u4['id']}/profile", headers=H1))["relation"] == "none", "친구 삭제")
check(c.delete(f"/friends/{u4['id']}", headers=H1).status_code == 404, "친구 아닌 사람 삭제 불가")

# ---------- 망한 요리 대회 (리그와 별개, 전체 참가) ----------
fb = ok(c.get("/battles/fail/current", headers=H1))
check(fb["kind"] == "fail" and fb["group_label"] == "전체" and fb["phase"] == "cooking", "망한 요리 대회 개최")
check(ok(c.get("/battles/fail/current", headers=H4))["id"] == fb["id"], "리그 상관없이 같은 대회")
fid = fb["id"]
f1 = ok(submit(H1, fid, "숯이 된 계란말이"))["submission"]["id"]
f4 = ok(submit(H4, fid, "폭발한 라면"))["submission"]["id"]
ok(submit(H2, fid, "녹아내린 치즈"))
check(ok(c.get("/battles/current", headers=H1))["kind"] == "league", "리그 대결과 따로 진행")
ok(c.post(f"/admin/battles/{fid}/phase", headers=A, json={"phase": "voting"}))
check(c.post(f"/submissions/{f1}/vote", headers=H3).status_code == 403, "망한 요리 대회도 참가자만 투표")
ok(c.post(f"/submissions/{f4}/vote", headers=H1))
ok(c.post(f"/submissions/{f4}/vote", headers=H2))
ok(c.post(f"/submissions/{f1}/vote", headers=H4))
ok(c.post(f"/admin/battles/{fid}/close", headers=A))
fr = ok(c.get(f"/battles/{fid}/results", headers=H4))
check([e["rank_points"] for e in fr["podium"]] == [3, 2], "망한 요리 대회 포인트 (3/2/1)")
check(fr["my_result"]["rank"] == 1 and not fr["my_result"]["can_share_recipe"], "망한 요리 우승은 레시피 공유 없음")
check(c.post(f"/submissions/{f4}/recipe", headers=H4, json=body).status_code == 400, "망한 요리 레시피 공유 불가")
check(ok(c.get("/battles/fail/current", headers=H1))["id"] != fid, "종료 후 새 망한 요리 대회")

print(f"✅ 스모크 테스트 {step}개 항목 전부 통과")
