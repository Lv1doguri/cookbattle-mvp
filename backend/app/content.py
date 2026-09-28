"""Tunable game rules and copy. Change numbers/text here, not in the routers."""
import datetime as dt

from .enums import Category, Tier, Tool

# ---- points & level -------------------------------------------------------
# 1P ≈ 10원. Level is driven by *lifetime earned* points (spending in the shop
# never lowers it). Lv.N needs 100*(2^(N-1) - 1) points: Lv2=100, Lv3=300,
# Lv4=700, Lv5=1,500, Lv6=3,100 ... (팀 수익화 문서 "포인트 분배 기준" 기준).
LEVEL_BASE_POINTS = 100


def level_threshold(level: int) -> int:
    if level <= 1:
        return 0
    return LEVEL_BASE_POINTS * (2 ** (level - 1) - 1)


# 2026-09-28 재조정: 가입만 해도 공짜 기프티콘에 너무 가까워지는 문제가 있어서(가입+첫대결 보너스만으로
# 편의점 1,000원권 120P의 절반), 무료로 거저 주는 값은 낮추고 "직접 대결해서 얻는" 보상 비중을 키웠어요.
SIGNUP_BONUS_POINTS = 10  # 가입 보너스 (1회)
FIRST_BATTLE_BONUS_POINTS = 15  # 첫 대결 참가 보너스 (1회, PARTICIPATION_POINTS와 별도로 더해짐)
PARTICIPATION_POINTS = 8  # paid when the entry is submitted
VOTE_POINTS = 2  # paid once per battle when a vote is cast, during the voting window
# 순위 보상. 3등까지는 확실히 크게, 그 아래는 완주 보상 개념으로 조금씩 줄여서 줘요 —
# 4등 밑이라고 0P가 되는 사람이 없게(2026-09-28: "4등인데 0P"라는 피드백으로 도입).
RANK_POINTS = {1: 80, 2: 50, 3: 30, 4: 20, 5: 15}
RANK_POINTS_FLOOR = 10  # 6등 이하는 전부 이만큼 (halved 대상이면 더 줄어요)


def rank_points_for(rank: int) -> int:
    return RANK_POINTS.get(rank, RANK_POINTS_FLOOR)
MIN_PARTICIPANTS = 3  # fewer than this and the battle is void (no ranking, no rank points)
RANK_POINTS_FULL_MIN_PARTICIPANTS = 10  # fewer than this (but >= MIN_PARTICIPANTS) and rank points are halved
STREAK_WEEKS = 3  # 이만큼 연속으로 매주 참가하면 보너스 (그 다음 STREAK_WEEKS주 연속 참가 시 또 지급)
STREAK_BONUS_POINTS = 20
REVIEW_POINTS = 1  # 레시피 후기 1건당
REVIEW_DAILY_CAP_POINTS = 3  # 후기로 하루에 받을 수 있는 포인트 상한

# 후기의 "실제로 해봤어요" 난이도 태그 (인증샷과 함께 쓰여요). 포인트는 REVIEW_POINTS 그대로 — 별도 보너스 없음.
DIFFICULTY_TAG_LABEL = {"easy": "쉬움 (원팬)", "normal": "보통", "hard": "귀찮음"}

# "이번 달 요리 N회" x this = "절약한 식비". 4,000 is what the design mock implies (8회 -> 32,000원).
SAVING_PER_COOKING_KRW = 4000

# ---- in-app camera photos -------------------------------------------------
# The photo is uploaded the moment it's taken; the server stamps captured_at. It must be attached
# to a battle entry within this window, and can be used only once (so old photos can't be recycled).
PHOTO_TTL = dt.timedelta(hours=1)
MAX_UPLOADS_PER_HOUR = 30

# 대결 참가 인증: 조작(사진 한 장만 어디서 주워옴)을 줄이려고 여러 각도 사진을 요구해요.
ENTRY_MIN_PHOTOS = 3  # 최소 각도별 인증샷 수 (재료/조리 중/완성 등)
ENTRY_MAX_PHOTOS = 6

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

# ---- shop seed: (name, price_points, required_level, photo filename under app/seed_photos/shop/) ----
# 가격은 원가 × 약 1.5 (2026-09-28: 포인트를 너무 쉽게 모아서 적자 위험이 있다는 피드백으로 1.2 -> 1.5로 상향)
SHOP_SEED = [
    ("편의점 1,000원권", 150, 1, "convenience-store.jpg"),
    ("저가 커피 아메리카노", 300, 2, "coffee.jpg"),
    ("학식 식권", 800, 3, "cafeteria-meal.jpg"),
    ("치킨 기프티콘", 3000, 5, "fried-chicken.jpg"),
]

# ---- official account + sample recipes ------------------------------------
# Recipes normally come from battle winners, so a fresh DB would show an empty recipe tab.
# These samples (authored by the "요리왕" official account) fill it until real winners exist.
OFFICIAL_NICKNAME = "요리왕"
OFFICIAL_EMAIL = "official@cookup.invalid"

# Recipes shown under the "자취 필수" quick filter. Curated by hand; battle winners' recipes aren't essential by default.
ESSENTIAL_RECIPES = {"김치볶음밥", "참치마요 덮밥", "비빔국수"}

# title -> filename under app/seed_photos/. 실제 요리 사진(자유 라이선스, Wikimedia Commons 출처).
# 출처/라이선스는 app/seed_photos/CREDITS.md 참고.
RECIPE_SEED_PHOTOS = {
    "김치볶음밥": "kimchi-bokkeumbap.jpg",
    "참치마요 덮밥": "tuna-mayo-bowl.jpg",
    "크림 파스타": "cream-pasta.jpg",
    "비빔국수": "bibim-guksu.jpg",
    "제육볶음": "jeyuk-bokkeum.jpg",
    "수제 라멘": "ramen.jpg",
    "닭가슴살 샐러드": "chicken-salad.jpg",
    "간장계란밥": "ganjang-gyeranbap.jpg",
    "통스팸 짜파구리 라자냐": "jjapaguri-lasagna.jpg",
}

# 레시피 딕셔너리 필드:
#   title, category, cost_krw, minutes, difficulty, win_label, tools,
#   ingredients[(name, amount)], steps[(text, minutes)],
#   value_score(가성비 지수 0~5), calories_kcal, portion_label, fail_safety_label, chef_tip
RECIPE_SEED = [
    dict(
        title="김치볶음밥", category=Category.rice, cost_krw=3500, minutes=15, difficulty=Tier.beginner,
        win_label="밥 요리 대결 1등", tools=[Tool.pan],
        ingredients=[("김치", "1컵"), ("밥", "1공기"), ("계란", "1개"), ("식용유", "1큰술")],
        steps=[
            ("김치를 잘게 썬다.", 2),
            ("팬에 기름을 두르고 김치를 볶는다.", 5),
            ("밥을 넣고 고루 볶는다.", 6),
        ],
        value_score=4.6, calories_kcal=620, portion_label="1인분 든든하게", fail_safety_label="원팬 요리",
        chef_tip="신 김치를 쓸 땐 설탕 반 스푼만 더해도 감칠맛이 확 살아나요. 마지막에 참기름 한 바퀴는 필수!",
    ),
    dict(
        title="참치마요 덮밥", category=Category.rice, cost_krw=2800, minutes=10, difficulty=Tier.beginner,
        win_label="5천원 이하 대결 1등", tools=[],
        ingredients=[("밥", "1공기"), ("참치캔", "1개"), ("마요네즈", "2큰술"), ("간장", "1작은술"), ("김가루", "약간")],
        steps=[
            ("참치캔의 기름을 뺀다.", 1),
            ("참치에 마요네즈와 간장을 넣고 섞는다.", 2),
            ("그릇에 밥을 담고 참치마요를 올린다.", 1),
            ("김가루를 뿌려 완성한다.", 1),
        ],
        value_score=4.7, calories_kcal=540, portion_label="한 그릇 뚝딱", fail_safety_label="실패 걱정 없음",
        chef_tip="마요네즈와 간장 비율은 2:1이 국룰이에요. 마지막에 와사비를 살짝 더하면 느끼함이 잡혀요.",
    ),
    dict(
        title="크림 파스타", category=Category.pasta, cost_krw=4500, minutes=20, difficulty=Tier.intermediate,
        win_label="면 요리 대결 1등", tools=[Tool.pan],
        ingredients=[("파스타 면", "1인분"), ("생크림", "200ml"), ("마늘", "3쪽"), ("베이컨", "3줄")],
        steps=[
            ("파스타를 소금물에 8분 삶는다.", 8),
            ("마늘과 베이컨을 볶다가 생크림을 부어 소스를 만든다.", 5),
            ("삶은 파스타를 소스에 넣는다.", 2),
            ("잘 섞어서 완성한다.", 1),
        ],
        value_score=4.5, calories_kcal=810, portion_label="1인분 푸짐하게", fail_safety_label="약불 필수",
        chef_tip="생크림이 끓어오르면 분리되니 마늘·베이컨을 볶은 후엔 불을 꼭 약하게 낮추고 나서 부어주세요.",
    ),
    dict(
        title="비빔국수", category=Category.noodle, cost_krw=3000, minutes=15, difficulty=Tier.beginner,
        win_label="면 요리 대결 1등", tools=[],
        ingredients=[("소면", "1인분"), ("고추장", "1큰술"), ("식초", "1큰술"), ("설탕", "1작은술"), ("참기름", "1큰술"), ("오이", "1/2개")],
        steps=[
            ("소면을 삶아 찬물에 헹군다.", 6),
            ("고추장, 식초, 설탕, 참기름으로 양념장을 만든다.", 3),
            ("오이를 채 썬다.", 2),
            ("면에 양념장과 오이를 올려 비빈다.", 2),
        ],
        value_score=4.8, calories_kcal=480, portion_label="시원하게 한 그릇", fail_safety_label="원팬 요리",
        chef_tip="면을 헹굴 땐 얼음물까지 써야 쫄깃함이 살아나요. 식초는 마지막에 넣어야 신맛이 안 날아가요.",
    ),
    dict(
        title="제육볶음", category=Category.meat, cost_krw=6500, minutes=25, difficulty=Tier.intermediate,
        win_label="고기 요리 대결 1등", tools=[Tool.pan],
        ingredients=[
            ("돼지고기 앞다리살", "200g"), ("양파", "1/2개"), ("대파", "1대"), ("고추장", "1큰술"),
            ("고춧가루", "1큰술"), ("간장", "1큰술"), ("설탕", "1작은술"), ("다진 마늘", "1작은술"),
        ],
        steps=[
            ("양념 재료를 섞어 고기에 버무려 10분 재운다.", 10),
            ("양파와 대파를 썬다.", 3),
            ("팬에 고기를 넣고 센 불에서 볶는다.", 7),
            ("채소를 넣고 한 번 더 볶아 완성한다.", 3),
        ],
        value_score=4.4, calories_kcal=690, portion_label="밥도둑 한 접시", fail_safety_label="센 불 주의",
        chef_tip="고기를 재울 때 사이다를 한 스푼 더하면 훨씬 부드러워져요. 센 불에서 빠르게 볶아야 육즙이 안 빠져요.",
    ),
    dict(
        title="수제 라멘", category=Category.noodle, cost_krw=11000, minutes=90, difficulty=Tier.advanced,
        win_label="면 요리 대결 1등", tools=[],
        ingredients=[("라멘 면", "1인분"), ("돼지 뼈 육수", "500ml"), ("차슈", "3장"), ("반숙란", "1개"), ("대파", "약간"), ("간장 타레", "2큰술")],
        steps=[
            ("육수를 끓여 간장 타레로 간을 맞춘다.", 40),
            ("면을 삶아 물기를 뺀다.", 5),
            ("그릇에 타레와 육수를 붓고 면을 넣는다.", 2),
            ("차슈, 반숙란, 대파를 올려 완성한다.", 3),
        ],
        value_score=4.3, calories_kcal=720, portion_label="든든한 한 그릇", fail_safety_label="정성 필요",
        chef_tip="타레는 하루 전날 미리 만들어두면 맛이 훨씬 깊어져요. 반숙란은 6분 30초가 황금 타이밍!",
    ),
    dict(
        title="닭가슴살 샐러드", category=Category.healthy, cost_krw=5500, minutes=15, difficulty=Tier.beginner,
        win_label="건강한 요리 대결 1등", tools=[Tool.pan],
        ingredients=[("닭가슴살", "1덩이"), ("양상추", "한 줌"), ("방울토마토", "5개"), ("올리브유", "1큰술"), ("발사믹 식초", "1큰술")],
        steps=[
            ("닭가슴살을 팬에 굽거나 삶아 식힌 뒤 찢는다.", 8),
            ("양상추와 방울토마토를 씻어 담는다.", 3),
            ("닭가슴살을 올린다.", 2),
            ("올리브유와 발사믹 식초를 뿌린다.", 2),
        ],
        value_score=4.6, calories_kcal=320, portion_label="다이어트 한 끼", fail_safety_label="실패 걱정 없음",
        chef_tip="닭가슴살은 밑간 후 30분만 재워도 훨씬 촉촉해요. 구운 직후 3분간 그대로 두면 육즙이 안 빠져요.",
    ),
    dict(
        title="간장계란밥", category=Category.rice, cost_krw=1500, minutes=5, difficulty=Tier.beginner,
        win_label="5천원 이하 대결 1등", tools=[Tool.pan],
        ingredients=[("밥", "1공기"), ("계란", "1개"), ("간장", "1큰술"), ("참기름", "1큰술"), ("버터", "1조각"), ("김가루", "약간")],
        steps=[
            ("팬에 버터를 녹이고 계란을 반숙으로 부친다.", 2),
            ("뜨거운 밥에 간장과 참기름을 넣고 비빈다.", 1),
            ("밥 위에 계란과 김가루를 올린다.", 1),
            ("노른자를 터뜨려 비벼 먹는다.", 1),
        ],
        value_score=4.9, calories_kcal=480, portion_label="1인분 초간단", fail_safety_label="실패 걱정 없음",
        chef_tip="간장은 국간장 반, 진간장 반으로 섞으면 짜지 않고 감칠맛이 살아나요. 버터는 마지막에 한 조각 더!",
    ),
    dict(
        title="통스팸 짜파구리 라자냐", category=Category.noodle, cost_krw=3800, minutes=12, difficulty=Tier.beginner,
        win_label="5천원 이하 대결 1등", tools=[Tool.pan],
        ingredients=[
            ("통조림 스팸", "200g"), ("짜파게티", "1봉"), ("너구리", "1봉"),
            ("모짜렐라 피자치즈", "1봉"), ("체다 슬라이스 치즈", "1장"), ("청양고추(선택)", "1/2개"),
        ],
        steps=[
            ("면을 평소보다 1분 덜 꼬들하게 삶고, 물을 반 컵만 남긴 뒤 짜파장 1봉과 너구리스프 반 봉을 섞어 자작하게 만든다.", 3),
            ("팬 바닥에 얇게 슬라이스한 스팸을 구워 깔고, 그 위로 양념된 면과 모짜렐라 치즈를 라자냐처럼 2단으로 켜켜이 쌓는다.", 4),
            ("팬 뚜껑을 덮고 약불로 3분, 치즈가 녹아내리면 체다 치즈를 얹고 후춧가루나 고춧가루를 뿌려 마무리한다.", 3),
        ],
        value_score=4.9, calories_kcal=780, portion_label="1.5인분 야식", fail_safety_label="원팬 요리",
        chef_tip="프라이팬 뚜껑이 없다면 호일이나 넓은 접시로 덮어도 돼요. 전자레인지라면 랩을 씌우고 포크로 구멍을 3개 뚫어 2분 30초만 돌리면 완벽하게 멜팅돼요.",
    ),
]
