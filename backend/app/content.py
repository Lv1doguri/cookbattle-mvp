"""Tunable game rules and copy. Change numbers/text here, not in the routers."""
import datetime as dt

from .enums import Category, Tier, Tool

# ---- points & level -------------------------------------------------------
# Level is driven by *lifetime earned* points (spending in the shop never lowers it).
# Lv.N needs 5*N*(N-1)/2 points: Lv2=5, Lv3=15, Lv4=30, Lv5=50 ...
LEVEL_STEP_POINTS = 5


def level_threshold(level: int) -> int:
    return LEVEL_STEP_POINTS * level * (level - 1) // 2


PARTICIPATION_POINTS = 1  # paid when the entry is submitted
RANK_POINTS = {1: 5, 2: 4, 3: 3}  # paid on top of participation when the battle is finalized
MIN_PARTICIPANTS = 3  # fewer than this and the battle is void (no ranking, no rank points)

# "이번 달 요리 N회" x this = "절약한 식비". 4,000 is what the design mock implies (8회 -> 32,000원).
SAVING_PER_COOKING_KRW = 4000

# ---- in-app camera photos -------------------------------------------------
# The photo is uploaded the moment it's taken; the server stamps captured_at. It must be attached
# to a battle entry within this window, and can be used only once (so old photos can't be recycled).
PHOTO_TTL = dt.timedelta(hours=1)
MAX_UPLOADS_PER_HOUR = 30

# ---- weekly group battles -------------------------------------------------
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

# ---- shop seed: (name, price_points, required_level) ----------------------
SHOP_SEED = [
    ("커피 기프티콘", 1000, 1),
    ("학식 식권", 800, 1),
    ("편의점 상품권", 3000, 2),
    ("치킨 기프티콘", 5000, 5),
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
