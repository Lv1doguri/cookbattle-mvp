"""Tunable game rules and copy. Change numbers/text here, not in the routers."""
import datetime as dt

from .enums import Category, Tier, Tool

# ---- points & level -------------------------------------------------------
# Level is driven by *lifetime earned* points (spending in the shop never lowers it).
# Numbers below come from the team's monetization/points plan (1P ≈ 10원), replacing the
# original placeholder economy that API_CONTRACT.md itself flagged as inconsistent with the
# shop prices (assumption #2: "포인트 경제가 안 맞아요").
# Lv.2=100P, Lv.3=300P, Lv.4=700P, Lv.5=1500P, then +LEVEL_STEP_AFTER_TABLE per level.
LEVEL_THRESHOLDS = [0, 100, 300, 700, 1500]
LEVEL_STEP_AFTER_TABLE = 800


def level_threshold(level: int) -> int:
    """Lifetime points needed to *be* this level (level_threshold(1) == 0)."""
    idx = level - 1
    if idx < len(LEVEL_THRESHOLDS):
        return LEVEL_THRESHOLDS[idx]
    extra_levels = idx - (len(LEVEL_THRESHOLDS) - 1)
    return LEVEL_THRESHOLDS[-1] + extra_levels * LEVEL_STEP_AFTER_TABLE


SIGNUP_BONUS = 30  # once, on signup (including Google signup) — "시작하자마자 목표가 보이게"
FIRST_BATTLE_BONUS = 30  # once, on a user's first-ever entry (on top of participation)
PARTICIPATION_POINTS = 10  # paid when the entry is submitted
VOTE_POINTS = 2  # paid once per battle when a vote is cast, during the voting window
RANK_POINTS = {1: 100, 2: 60, 3: 40}  # paid on top of participation when the battle is finalized
RANK_FULL_MIN_PARTICIPANTS = 10  # fewer participants than this -> rank points are halved
MIN_PARTICIPANTS = 3  # fewer than this and the battle is void (no ranking, no rank points)
STREAK_WEEKS = 3  # N consecutive weekly battles joined -> streak bonus
STREAK_BONUS = 20
REVIEW_POINTS = 1  # per recipe review/comment written
REVIEW_DAILY_CAP = 3  # review points are capped per calendar day (KST) to stop spam
POINTS_EXPIRE_AFTER = dt.timedelta(days=365)  # spendable balance only; lifetime total/level untouched

# ---- shop anti-loss safeguards ---------------------------------------------
MAX_EXCHANGES_PER_MONTH_PER_USER = 2

# "이번 달 요리 N회" x this = "절약한 식비". 4,000 is what the design mock implies (8회 -> 32,000원).
SAVING_PER_COOKING_KRW = 4000

# ---- email verification (signup isn't final until the link is clicked) ----
# Resend attempts share services.throttle's login rate limit (10 per 10 minutes per key).
EMAIL_VERIFICATION_TTL = dt.timedelta(minutes=30)

# ---- in-app camera photos -------------------------------------------------
# The photo is uploaded the moment it's taken; the server stamps captured_at. It must be attached
# to a battle entry within this window, and can be used only once (so old photos can't be recycled).
PHOTO_TTL = dt.timedelta(hours=1)
MAX_UPLOADS_PER_HOUR = 30
# Perceptual-hash (dHash, 64-bit) distance below which two photos count as "the same picture"
# (survives resizing/recompression/minor brightness changes). On top of camera-only + TTL + single
# use, this catches someone re-photographing a screen/printout of an old photo. 0-64 scale.
PHOTO_DUP_HAMMING_DISTANCE = 10

# ---- angle-photo verification (proof the dish is really yours) ------------
# On top of camera-only + TTL + reuse detection, every battle also requires a *second* photo shot
# from an angle picked at random when the battle is created (services.battles). A photo lifted from
# the internet can't be re-shot to order from an unpredictable angle, so this is the main defense
# against submitting someone else's picture. services/vision.py checks (via a vision model) that
# the two photos show the same dish and that the second one actually matches the requested angle.
ANGLE_POOL = [
    {"id": "top", "label": "위에서 내려다본 모습", "instruction": "음식을 바로 위에서 내려다보고 찍어주세요"},
    {"id": "side", "label": "옆에서 찍은 모습", "instruction": "그릇을 옆에서 찍어주세요"},
    {"id": "closeup", "label": "가까이서 찍은 클로즈업", "instruction": "음식에 최대한 가까이 다가가서 찍어주세요"},
    {"id": "hand", "label": "손(도구)이 함께 나온 모습", "instruction": "젓가락이나 숟가락을 든 손과 함께 찍어주세요"},
]
ANGLE_BY_ID = {a["id"]: a for a in ANGLE_POOL}

# ---- voting (after a battle's cooking period ends) -------------------------
# 대회가 끝나면 바로 집계하지 않고, 24시간 동안 투표만 받은 뒤에 집계해요.
VOTING_WINDOW = dt.timedelta(hours=24)

# ---- weekly group battles ("오늘의 대결") -----------------------------------
# A battle runs Monday 00:00 KST -> next Monday 00:00 KST, one per skill group.
BATTLE_EPOCH = dt.date(2026, 8, 31)  # a Monday; week 0 uses BATTLE_THEMES[0]
BATTLE_THEMES = [
    {
        "theme": "밥 요리",
        Tier.beginner: "간단한 밥 요리면 OK",
        Tier.intermediate: "밥이 메인인 든든한 한 끼",
        Tier.advanced: "밥부터 소스까지 정성껏 만든 요리",
    },
    {
        "theme": "면 요리",
        Tier.beginner: "간단한 면 요리면 OK",
        Tier.intermediate: "소스까지 직접 만든 면 요리",
        Tier.advanced: "면부터 직접 만든 면 요리",
    },
    {
        "theme": "5천원 이하",
        Tier.beginner: "5,000원 이하로 만든 간단한 요리면 OK",
        Tier.intermediate: "5,000원 이하로 완성한 든든한 한 끼",
        Tier.advanced: "5,000원 이하로 만든 정성 요리",
    },
    {
        "theme": "계란 요리",
        Tier.beginner: "간단한 계란 요리면 OK",
        Tier.intermediate: "계란이 메인인 든든한 한 끼",
        Tier.advanced: "소스까지 직접 만든 계란 요리",
    },
    {
        "theme": "라면",
        Tier.beginner: "라면에 한 가지만 더해도 OK",
        Tier.intermediate: "라면을 색다르게 업그레이드한 한 끼",
        Tier.advanced: "육수부터 직접 만든 라면 요리",
    },
    {
        "theme": "고기 요리",
        Tier.beginner: "간단한 고기 요리면 OK",
        Tier.intermediate: "고기가 메인인 든든한 한 끼",
        Tier.advanced: "양념·소스까지 직접 만든 고기 요리",
    },
    {
        "theme": "건강한 요리",
        Tier.beginner: "채소를 곁들인 간단한 요리면 OK",
        Tier.intermediate: "영양 균형을 맞춘 든든한 한 끼",
        Tier.advanced: "재료 손질부터 신경 쓴 건강 요리",
    },
    {
        "theme": "디저트",
        Tier.beginner: "간단한 디저트면 OK",
        Tier.intermediate: "크림·시럽까지 직접 만든 디저트",
        Tier.advanced: "반죽부터 직접 만든 디저트",
    },
]

# ---- theme battles ("테마 대결") ---------------------------------------------
# 실력 그룹 구분 없이 전체가 함께 참가하는 대결. 요일별 대결보다 며칠 더 길게 진행돼요.
# (디자인에 그룹별인지 전체 공통인지 명시가 없어서 "전체 공통"으로 가정했어요 — API_CONTRACT.md 참고)
THEME_EPOCH = dt.date(2026, 8, 31)  # 요일별 대결과 같은 기준일
THEME_COOKING_DAYS = 3
THEME_BATTLES = [
    {"theme": "망한 요리 대회", "description": "누구보다 처참하게 실패해보세요"},
    {"theme": "한 그릇 요리 대회", "description": "설거지거리 하나로 끝내는 한 그릇 요리"},
    {"theme": "자취 아이돌 대회", "description": "자취방에서 가장 자랑하고 싶은 요리"},
    {"theme": "매운맛 대회", "description": "맵기로 승부하는 요리"},
]

# ---- shop seed: (name, price_points, required_level, monthly_limit) -------
# monthly_limit caps how many can be exchanged per calendar month (auto-resets); None = unlimited.
# Prices follow the team's 1P ≈ 10원 plan, roughly cost x1.2.
SHOP_SEED = [
    ("편의점 1,000원권", 120, 1, None),
    ("아메리카노 기프티콘", 240, 2, 30),
    ("학식 식권", 650, 3, 20),
    ("치킨 기프티콘", 2600, 5, 10),
]

# ---- official account + sample recipes ------------------------------------
# Recipes normally come from battle winners, so a fresh DB would show an empty recipe tab.
# These samples (authored by the "요리왕" official account) fill it until real winners exist.
OFFICIAL_NICKNAME = "요리왕"
OFFICIAL_EMAIL = "official@cookup.invalid"

# Recipes shown under the "자취 필수" quick filter. Curated by hand; battle winners' recipes aren't essential by default.
ESSENTIAL_RECIPES = {"김치볶음밥", "참치마요 덮밥", "비빔국수"}

# (title, category, cost_krw, minutes, difficulty, win_label, tools, ingredients[(name, amount)], steps[])
RECIPE_SEED = [
    (
        "김치볶음밥", Category.rice, 3500, 15, Tier.beginner, "밥 요리 대결 1등", [Tool.pan],
        [("김치", "1컵"), ("밥", "1공기"), ("계란", "1개"), ("식용유", "1큰술")],
        ["김치를 잘게 썬다.", "팬에 기름을 두르고 김치를 볶는다.", "밥을 넣고 고루 볶는다."],
    ),
    (
        "참치마요 덮밥", Category.rice, 2800, 10, Tier.beginner, "5천원 이하 대결 1등", [],
        [("밥", "1공기"), ("참치캔", "1개"), ("마요네즈", "2큰술"), ("간장", "1작은술"), ("김가루", "약간")],
        ["참치캔의 기름을 뺀다.", "참치에 마요네즈와 간장을 넣고 섞는다.", "그릇에 밥을 담고 참치마요를 올린다.", "김가루를 뿌려 완성한다."],
    ),
    (
        "크림 파스타", Category.pasta, 4500, 20, Tier.intermediate, "면 요리 대결 1등", [Tool.pan],
        [("파스타 면", "1인분"), ("생크림", "200ml"), ("마늘", "3쪽"), ("베이컨", "3줄")],
        ["파스타를 소금물에 8분 삶는다.", "마늘과 베이컨을 볶다가 생크림을 부어 소스를 만든다.", "삶은 파스타를 소스에 넣는다.", "잘 섞어서 완성한다."],
    ),
    (
        "비빔국수", Category.noodle, 3000, 15, Tier.beginner, "면 요리 대결 1등", [],
        [("소면", "1인분"), ("고추장", "1큰술"), ("식초", "1큰술"), ("설탕", "1작은술"), ("참기름", "1큰술"), ("오이", "1/2개")],
        ["소면을 삶아 찬물에 헹군다.", "고추장, 식초, 설탕, 참기름으로 양념장을 만든다.", "오이를 채 썬다.", "면에 양념장과 오이를 올려 비빈다."],
    ),
    (
        "제육볶음", Category.meat, 6500, 25, Tier.intermediate, "고기 요리 대결 1등", [Tool.pan],
        [("돼지고기 앞다리살", "200g"), ("양파", "1/2개"), ("대파", "1대"), ("고추장", "1큰술"), ("고춧가루", "1큰술"), ("간장", "1큰술"), ("설탕", "1작은술"), ("다진 마늘", "1작은술")],
        ["양념 재료를 섞어 고기에 버무려 10분 재운다.", "양파와 대파를 썬다.", "팬에 고기를 넣고 센 불에서 볶는다.", "채소를 넣고 한 번 더 볶아 완성한다."],
    ),
    (
        "수제 라멘", Category.noodle, 11000, 90, Tier.advanced, "면 요리 대결 1등", [],
        [("라멘 면", "1인분"), ("돼지 뼈 육수", "500ml"), ("차슈", "3장"), ("반숙란", "1개"), ("대파", "약간"), ("간장 타레", "2큰술")],
        ["육수를 끓여 간장 타레로 간을 맞춘다.", "면을 삶아 물기를 뺀다.", "그릇에 타레와 육수를 붓고 면을 넣는다.", "차슈, 반숙란, 대파를 올려 완성한다."],
    ),
    (
        "닭가슴살 샐러드", Category.healthy, 5500, 15, Tier.beginner, "건강한 요리 대결 1등", [Tool.pan],
        [("닭가슴살", "1덩이"), ("양상추", "한 줌"), ("방울토마토", "5개"), ("올리브유", "1큰술"), ("발사믹 식초", "1큰술")],
        ["닭가슴살을 팬에 굽거나 삶아 식힌 뒤 찢는다.", "양상추와 방울토마토를 씻어 담는다.", "닭가슴살을 올린다.", "올리브유와 발사믹 식초를 뿌린다."],
    ),
    (
        "바나나 머그케이크", Category.dessert, 2500, 5, Tier.beginner, "디저트 대결 1등", [Tool.microwave],
        [("바나나", "1개"), ("계란", "1개"), ("박력분", "3큰술"), ("우유", "3큰술"), ("설탕", "1큰술")],
        ["머그컵에 바나나를 으깬다.", "계란, 박력분, 우유, 설탕을 넣고 섞는다.", "전자레인지에 2분 30초 돌린다.", "식혀서 먹는다."],
    ),
]
