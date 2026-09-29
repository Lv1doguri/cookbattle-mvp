"""Fills the app with a realistic, well-used demo account for showing off every
feature at once (발표/데모용). Separate from `seed_all` (shop + base recipes),
which every server start already runs — this is opt-in and heavier.

Idempotent: does nothing if the demo user already exists, so re-running the
server (or this script) never duplicates data.

Usage (from `backend/`, venv active, after the server has run at least once):

    python -m app.seed_demo

Demo login: inha1234 / induck1234
"""
import datetime as dt
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import clock
from .config import settings
from .content import (
    FIRST_BATTLE_BONUS_POINTS,
    MIN_PARTICIPANTS,
    PARTICIPATION_POINTS,
    RANK_POINTS_FULL_MIN_PARTICIPANTS,
    RECIPE_SEED_PHOTOS,
    REVIEW_POINTS,
    SIGNUP_BONUS_POINTS,
    STREAK_BONUS_POINTS,
    STREAK_DAYS,
    THEME_BATTLES,
    THEME_COOKING_DAYS,
    THEME_EPOCH,
    VOTING_WINDOW,
    rank_points_for,
)
from .database import Base, SessionLocal, engine
from .enums import BattleKind, Category, Tier, Tool
from .models import Battle, Entry, Ingredient, Photo, Recipe, RecipeSave, RecipeTool, Review, Step, User
from .security import hash_password
from .seed import SEED_PHOTOS_DIR, seed_all
from .services.points import grant_points, level_for

DEMO_USERNAME = "inha1234"
DEMO_PASSWORD = "induck1234"
DEMO_NICKNAME = "발표자"

DEMO_BATTLE_PHOTOS_DIR = SEED_PHOTOS_DIR / "demo_battle"

# 라면 대결용 5개 메뉴. "수제 라멘"은 원래 레시피 시드 사진을 그대로 재사용해요.
RAMEN_DISH_PHOTOS = {
    "투움바라면": DEMO_BATTLE_PHOTOS_DIR / "tuumba-ramen.jpg",
    "해물라면": DEMO_BATTLE_PHOTOS_DIR / "haemul-ramen.jpg",
    "수제 라멘": SEED_PHOTOS_DIR / "ramen.jpg",
    "크림새우라면": DEMO_BATTLE_PHOTOS_DIR / "cream-shrimp-ramen.jpg",
    "돈코츠비빔라면": DEMO_BATTLE_PHOTOS_DIR / "tonkotsu-bibim-ramen.jpg",
}

# 이력에 쓰는 커스텀 요리 이름(예: "매운 김치볶음밥")은 기본 레시피 시드 사진이 없어서,
# 제일 비슷한 시드 사진으로 매핑해요.
EXTRA_DISH_PHOTOS = {
    "매운 김치볶음밥": SEED_PHOTOS_DIR / RECIPE_SEED_PHOTOS["김치볶음밥"],
    "매콤 비빔국수": SEED_PHOTOS_DIR / RECIPE_SEED_PHOTOS["비빔국수"],
}

FILLER_NICKNAMES = ["자취요정민지", "프라이팬장인", "자취9년차", "동네반찬왕", "야식마스터", "불맛손맛"]

# 우승 레시피 공유 시 채울 필드 (POST /entries/{id}/recipe 와 같은 모양).
SHARED_RECIPE_DATA = {
    "간장계란밥": dict(
        category=Category.rice, price=2000, minutes=8, difficulty=Tier.beginner, tools=[],
        ingredients=[("밥", "1공기"), ("계란", "2개"), ("간장", "1.5큰술"), ("참기름", "1큰술"), ("버터", "약간")],
        steps=["계란은 반숙 후라이로 부친다.", "뜨거운 밥에 버터를 올려 녹인다.", "간장과 참기름을 넣고 비빈다.", "계란후라이를 올려 완성한다."],
    ),
    "매운 김치볶음밥": dict(
        category=Category.rice, price=4000, minutes=15, difficulty=Tier.intermediate, tools=[Tool.pan],
        ingredients=[("신김치", "1.5컵"), ("밥", "1공기"), ("스팸", "1/3캔"), ("고추장", "1작은술"), ("계란후라이", "1개")],
        steps=["신김치와 스팸을 잘게 썬다.", "팬에 스팸을 먼저 볶아 기름을 낸다.", "김치와 고추장을 넣고 볶는다.", "밥을 넣고 고루 볶은 뒤 계란후라이를 올린다."],
    ),
}


def _copy_photo(src: Path) -> str:
    filename = f"seed-{uuid.uuid4().hex}{src.suffix}"
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, Path(settings.upload_dir) / filename)
    return filename


def _dish_photo_path(title: str) -> Path:
    if title in RAMEN_DISH_PHOTOS:
        return RAMEN_DISH_PHOTOS[title]
    if title in EXTRA_DISH_PHOTOS:
        return EXTRA_DISH_PHOTOS[title]
    return SEED_PHOTOS_DIR / RECIPE_SEED_PHOTOS[title]


def _photo(db: Session, user_id: int, title: str, captured_at: dt.datetime) -> Photo:
    p = Photo(user_id=user_id, filename=_copy_photo(_dish_photo_path(title)), captured_at=captured_at)
    db.add(p)
    db.flush()
    return p


def _make_user(db: Session, *, username: str, nickname: str, password: str, tier: Tier, created_at: dt.datetime) -> User:
    u = User(
        username=username, nickname=nickname, password_hash=hash_password(password),
        tier=tier, points=0, total_points=0, created_at=created_at,
    )
    db.add(u)
    db.flush()
    return u


def _get_fillers(db: Session, created_at: dt.datetime) -> List[User]:
    fillers = []
    for i, nick in enumerate(FILLER_NICKNAMES, start=1):
        u = db.scalar(select(User).where(User.username == f"demo_cook{i}"))
        if u is None:
            u = _make_user(
                db, username=f"demo_cook{i}", nickname=nick, password=uuid.uuid4().hex,
                tier=Tier.intermediate, created_at=created_at,
            )
        fillers.append(u)
    return fillers


def _add_entry(db: Session, battle: Battle, user: User, dish: str, votes: int, created_at: dt.datetime) -> Entry:
    photo = _photo(db, user.id, dish, created_at)
    entry = Entry(
        battle_id=battle.id, user_id=user.id, photo_id=photo.id,
        dish_name=dish, vote_count=votes, created_at=created_at,
    )
    db.add(entry)
    db.flush()
    return entry


def _finalize(db: Session, battle: Battle, entries_desc: List[Entry], finalized_at: dt.datetime) -> None:
    """Ranks entries (already vote-sorted desc) and pays rank rewards — same formula
    as the live app's finalize step (services.battles._finalize), kept as a small
    self-contained copy here so this script doesn't reach into router-layer internals."""
    n = len(entries_desc)
    half = MIN_PARTICIPANTS <= n < RANK_POINTS_FULL_MIN_PARTICIPANTS
    for rank, entry in enumerate(entries_desc, start=1):
        user = db.get(User, entry.user_id)
        reward = rank_points_for(rank)
        if half:
            reward //= 2
        if reward:
            grant_points(db, user, reward, reason="rank_reward", ref_type="entry", ref_id=entry.id)
        entry.rank = rank
        entry.rank_points = reward
    battle.finalized_at = finalized_at
    db.commit()


def _join_as_demo_user(db: Session, battle: Battle, dish: str, votes: int, created_at: dt.datetime, user: User) -> Entry:
    """Mirrors what POST /battles/{id}/entries grants (participation, first-battle,
    streak bonus) for the demo user's own history entries."""
    is_first_ever = db.scalar(select(Entry.id).where(Entry.user_id == user.id)) is None
    entry = _add_entry(db, battle, user, dish, votes, created_at)

    grant_points(db, user, PARTICIPATION_POINTS, reason="participation", ref_type="entry", ref_id=entry.id)
    if is_first_ever:
        grant_points(db, user, FIRST_BATTLE_BONUS_POINTS, reason="first_battle_bonus", ref_type="entry", ref_id=entry.id)

    if user.streak_last_week == battle.week_start - dt.timedelta(days=1):
        user.streak_weeks += 1
    else:
        user.streak_weeks = 1
    user.streak_last_week = battle.week_start
    if user.streak_weeks % STREAK_DAYS == 0:
        grant_points(db, user, STREAK_BONUS_POINTS, reason="streak_bonus", ref_type="entry", ref_id=entry.id)
    db.commit()
    return entry


def _daily_battle(
    db: Session, *, tier: Tier, theme: str, description: str, week_start: dt.date,
    starts_at: dt.datetime, ends_at: dt.datetime, voting_ends_at: dt.datetime,
) -> Battle:
    b = Battle(
        kind=BattleKind.daily, tier=tier, theme=theme, description=description, week_start=week_start,
        starts_at=starts_at, ends_at=ends_at, voting_ends_at=voting_ends_at,
    )
    db.add(b)
    db.flush()
    return b


def _share_recipe(db: Session, entry: Entry, *, name: str, category: Category, price: int, minutes: int,
                   difficulty: Tier, tools: List[Tool], ingredients: List[Tuple[str, Optional[str]]],
                   steps: List[str], win_label: str, created_at: dt.datetime) -> Recipe:
    photo = db.get(Photo, entry.photo_id)
    recipe = Recipe(
        author_id=entry.user_id, entry_id=entry.id, title=name, category=category,
        cost_krw=price, cook_minutes=minutes, difficulty=difficulty, win_label=win_label,
        photo_filename=photo.filename, created_at=created_at,
    )
    recipe.ingredients = [Ingredient(position=i, name=n, amount=a) for i, (n, a) in enumerate(ingredients)]
    recipe.steps = [Step(position=i + 1, text=t) for i, t in enumerate(steps)]
    recipe.tools = [RecipeTool(tool=t) for t in tools]
    db.add(recipe)
    db.flush()
    return recipe


def seed_demo(db: Session) -> None:
    if db.scalar(select(User.id).where(User.username == DEMO_USERNAME)) is not None:
        print(f"'{DEMO_USERNAME}' already exists — skipping (delete the user, or the DB, to reseed).")
        return

    seed_all(db)  # shop + base recipes, in case this runs before the server ever has

    now = clock.utcnow()
    today = clock.kst_date(now)

    demo = _make_user(
        db, username=DEMO_USERNAME, nickname=DEMO_NICKNAME, password=DEMO_PASSWORD,
        tier=Tier.intermediate, created_at=now - dt.timedelta(days=9),
    )
    grant_points(db, demo, SIGNUP_BONUS_POINTS, reason="signup_bonus")

    fillers = _get_fillers(db, now - dt.timedelta(days=9))

    # ---- 지난 7일간 매일 대결 이력 (오래된 것부터: streak/첫대결 보너스가 순서대로 쌓여요) -----------
    # 정확히 STREAK_DAYS(7)일을 채워서 "일주일 개근" 보너스가 마지막 날 한 번 터져요.
    # share=False인 마지막 날(면 요리, 1등)은 일부러 레시피 공유를 안 해뒀어요 — 발표 중
    # "비법 레시피 공유하기" 버튼을 직접 눌러 보여주는 몫으로 남겨둔 거예요.
    history = [
        # (days_ago, theme, description, dish, my_votes, filler_votes(desc), share)
        (7, "계란 요리", "계란이 메인인 든든한 한 끼", "간장계란밥", 3, [2, 1], True),
        (6, "고기 요리", "고기가 메인인 든든한 한 끼", "제육볶음", 4, [5, 3, 2, 1], False),
        (5, "건강한 요리", "영양 균형을 맞춘 든든한 한 끼", "닭가슴살 샐러드", 3, [5, 4, 2], False),
        (4, "밥 요리", "밥이 메인인 든든한 한 끼", "매운 김치볶음밥", 6, [5, 4, 3, 2], True),
        (3, "5천원 이하", "5,000원 이하로 완성한 든든한 한 끼", "참치마요 덮밥", 4, [5, 3, 2, 1], False),
        (2, "라면", "라면을 색다르게 업그레이드한 한 끼", "수제 라멘", 5, [6, 3, 2, 1], False),
        (1, "면 요리", "소스까지 직접 만든 면 요리", "매콤 비빔국수", 7, [5, 4, 3, 2], False),
    ]

    shared_recipes: dict = {}
    for days_ago, theme, description, dish, my_votes, filler_votes, share in history:
        day = today - dt.timedelta(days=days_ago)
        starts_at = clock.kst_day_bounds(day)[0]
        # day가 오늘에 가까울수록(특히 days_ago=1) voting_ends_at이 실제 시간 기준으로 아직 미래일
        # 수 있어요(투표 마감 전인데 이미 순위/포인트가 매겨진 모순 상태). 그래서 무조건 지금보다
        # 확실히 과거가 되게 안전 마진을 둬요.
        ends_at = min(clock.kst_day_bounds(day + dt.timedelta(days=1))[0], now - VOTING_WINDOW - dt.timedelta(hours=1))
        voting_ends_at = ends_at + VOTING_WINDOW
        battle = _daily_battle(
            db, tier=Tier.intermediate, theme=theme, description=description, week_start=day,
            starts_at=starts_at, ends_at=ends_at, voting_ends_at=voting_ends_at,
        )
        created_at = starts_at + dt.timedelta(hours=12)
        my_entry = _join_as_demo_user(db, battle, dish, my_votes, created_at, demo)
        entries = [my_entry]
        for filler, votes in zip(fillers, filler_votes):
            entries.append(_add_entry(db, battle, filler, dish, votes, created_at + dt.timedelta(minutes=1)))
        entries.sort(key=lambda e: e.vote_count, reverse=True)
        _finalize(db, battle, entries, voting_ends_at + dt.timedelta(minutes=1))

        if share:
            data = SHARED_RECIPE_DATA[dish]
            recipe = _share_recipe(
                db, my_entry, name=dish, win_label=f"{theme} 대결 1등",
                created_at=voting_ends_at + dt.timedelta(minutes=5), **data,
            )
            shared_recipes[dish] = recipe.id

    # ---- 오늘 대결 (3개 그룹, '내 그룹'은 아직 참가 전 — 발표 중 실제로 참가해 보이는 용도) -------
    tier_labels = [Tier.beginner, Tier.intermediate, Tier.advanced]
    tier_desc = {
        Tier.beginner: "라면에 한 가지만 더해도 OK",
        Tier.intermediate: "라면을 색다르게 업그레이드한 한 끼",
        Tier.advanced: "육수부터 직접 만든 라면 요리",
    }
    today_starts = clock.kst_day_bounds(today)[0]
    today_ends = clock.kst_day_bounds(today + dt.timedelta(days=1))[0]
    for tier in tier_labels:
        battle = _daily_battle(
            db, tier=tier, theme="라면", description=tier_desc[tier], week_start=today,
            starts_at=today_starts, ends_at=today_ends, voting_ends_at=today_ends + VOTING_WINDOW,
        )
        for filler, dish in zip(fillers[:2], ["수제 라멘", "투움바라면"]):
            _add_entry(db, battle, filler, dish, 0, now - dt.timedelta(hours=3))

    # 어제 대결 -> 대결 홈의 "지난 대결 결과" 카드. 중급은 위 7일 이력의 하루 전(면 요리) 대결이
    # 이미 이 자리를 채우므로, 초급/상급만 따로 채워요.
    yesterday = today - dt.timedelta(days=1)
    yesterday_starts = clock.kst_day_bounds(yesterday)[0]
    # 위 이력 루프와 같은 이유로, 투표 마감이 실제 "지금"보다 미래가 되지 않게 안전하게 당겨요.
    yesterday_ends = min(clock.kst_day_bounds(today)[0], now - VOTING_WINDOW - dt.timedelta(hours=1))
    for tier in (Tier.beginner, Tier.advanced):
        prior_battle = _daily_battle(
            db, tier=tier, theme="라면", description=tier_desc[tier], week_start=yesterday,
            starts_at=yesterday_starts, ends_at=yesterday_ends, voting_ends_at=yesterday_ends + VOTING_WINDOW,
        )
        prior_entries = []
        for filler, (dish, votes) in zip(fillers, [("투움바라면", 5), ("해물라면", 4), ("수제 라멘", 3), ("크림새우라면", 2), ("돈코츠비빔라면", 1)]):
            prior_entries.append(_add_entry(db, prior_battle, filler, dish, votes, yesterday_starts + dt.timedelta(hours=12)))
        _finalize(db, prior_battle, prior_entries, yesterday_ends + dt.timedelta(minutes=1))

    # ---- 테마 대결: 투표 진행 중 상태로 (대결 홈의 "지난 대회 투표하기" + 실시간 랭킹 미리보기) ------
    cycle_index = (today - THEME_EPOCH).days // THEME_COOKING_DAYS
    cycle_start = THEME_EPOCH + dt.timedelta(days=cycle_index * THEME_COOKING_DAYS)
    schedule = THEME_BATTLES[cycle_index % len(THEME_BATTLES)]
    theme_starts = clock.kst_day_bounds(cycle_start)[0]
    theme_ends = now - dt.timedelta(hours=2)  # 방금 요리 마감, 투표 진행 중
    theme_battle = Battle(
        kind=BattleKind.theme, tier=None, theme=schedule["theme"], description=schedule["description"],
        week_start=cycle_start, starts_at=theme_starts, ends_at=theme_ends, voting_ends_at=theme_ends + VOTING_WINDOW,
    )
    db.add(theme_battle)
    db.flush()
    for filler, (dish, votes) in zip(fillers, [("김치볶음밥", 5), ("참치마요 덮밥", 4), ("제육볶음", 3), ("비빔국수", 2), ("수제 라멘", 1)]):
        _add_entry(db, theme_battle, filler, dish, votes, theme_starts + dt.timedelta(days=1))

    db.commit()

    # ---- 후기 3개 + 저장한 레시피 3개 (계란 요리 승리 레시피 하나, 원조 시드 레시피 둘) ---------------
    def _official_recipe(title: str) -> Recipe:
        return db.scalar(select(Recipe).where(Recipe.title == title, Recipe.entry_id.is_(None)))

    kimchi = _official_recipe("김치볶음밥")
    cream_pasta = _official_recipe("크림 파스타")
    jjapaguri = _official_recipe("통스팸 짜파구리 라자냐")
    review_photo = _copy_photo(SEED_PHOTOS_DIR / RECIPE_SEED_PHOTOS["크림 파스타"])

    reviews = [
        Review(recipe_id=kimchi.id, author_id=demo.id, text="자취 n년차인데 이건 진짜 국룰이에요. 신김치로 하면 더 맛있어요!"),
        Review(
            recipe_id=cream_pasta.id, author_id=demo.id,
            text="베이컨 두 배로 넣었더니 훨씬 고소해요. 자취방 인덕션으로도 문제없이 완성!",
            photo_filename=review_photo, rating=5, difficulty_tag="normal",
        ),
        Review(
            recipe_id=jjapaguri.id, author_id=demo.id,
            text="통스팸 짜파구리 라자냐 진짜 밤 11시에 만들어봤는데 치즈 녹는 거 보고 반함... 재현율 100%",
            rating=5, difficulty_tag="easy",
        ),
    ]
    db.add_all(reviews)
    db.flush()
    for r in reviews:
        grant_points(db, demo, REVIEW_POINTS, reason="review", ref_type="review", ref_id=r.id)

    db.add_all(RecipeSave(user_id=demo.id, recipe_id=rid) for rid in (kimchi.id, cream_pasta.id, jjapaguri.id))
    db.commit()

    # 7일치 이력만으론 상점을 데모하기엔 포인트가 너무 적어요(한 달치로 늘리면 자연스럽게 이 정도는
    # 쌓여요). "몇 주 더 이렇게 활동했다"는 셈 치고 시연용으로 살짝 얹어줘요 — 레벨업/구매 흐름을
    # 실제로 눌러볼 수 있게.
    grant_points(db, demo, 375, reason="demo_catchup", ref_type=None, ref_id=None)
    db.commit()

    print(
        f"Seeded demo account '{DEMO_USERNAME}' / '{DEMO_PASSWORD}' — "
        f"Lv.{level_for(demo.total_points)}, {demo.points}P (누적 {demo.total_points}P), {demo.streak_weeks}일 연속 참가."
    )
    print(f"Shared recipes: {shared_recipes}")
    print("오늘의 라면 대결(중급)은 아직 안 들어가 있어요 — 발표 중 실제로 참가해 보여주세요.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo(db)
