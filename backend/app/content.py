"""Tunable game rules and copy. Change numbers/text here, not in the routers."""
import datetime as dt

from .enums import ShopCategory, Tier

# ---- XP / level ----
XP_PER_LEVEL = 500  # level = xp // 500 + 1  (1,250 XP -> Lv.3, next level at 1,500)

# ---- rewards ----
BASE_POST_XP = 50
BASE_POST_COINS = 30
DAILY_BASE_REWARD_LIMIT = 3  # non-battle posts per KST day that still earn BASE_* (anti-farming)
LIKE_XP = 10  # battle entry: XP the author (and the entry's score) gets per like from someone else

BATTLE_REWARDS = {  # (xp, coins) for entering a battle
    Tier.beginner: (150, 50),
    Tier.intermediate: (200, 80),
    Tier.advanced: (300, 120),
}

# ---- camera-certified photos ----
PHOTO_TTL = dt.timedelta(hours=1)  # a photo must be attached to a post within this window
MAX_UPLOADS_PER_HOUR = 30

# ---- weekly battle schedule (index 0 = Monday) ----
WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

WEEKLY_THEMES = [
    {
        "theme": "면 요리",
        Tier.beginner: "면을 활용한 간단한 요리",
        Tier.intermediate: "소스까지 직접 만든 면 요리",
        Tier.advanced: "면부터 직접 만든 면 요리",
    },
    {
        "theme": "계란 요리",
        Tier.beginner: "계란으로 만드는 간단한 요리",
        Tier.intermediate: "계란을 주재료로 한 든든한 한 그릇",
        Tier.advanced: "계란 조리 기술을 살린 정성 요리",
    },
    {
        "theme": "밥 요리",
        Tier.beginner: "밥으로 뚝딱 만드는 간단한 요리",
        Tier.intermediate: "밥에 소스와 고명을 더한 요리",
        Tier.advanced: "밥 짓기부터 정성껏 만든 한 상",
    },
    {
        "theme": "감자 요리",
        Tier.beginner: "감자로 만드는 간단한 요리",
        Tier.intermediate: "감자를 다양하게 활용한 요리",
        Tier.advanced: "감자 손질부터 완성까지 직접 만든 요리",
    },
    {
        "theme": "5천원 이하",
        Tier.beginner: "5,000원 이하로 만드는 간단한 요리",
        Tier.intermediate: "5,000원 이하로 완성하는 든든한 한 끼",
        Tier.advanced: "5,000원 이하로 만드는 정성 요리",
    },
    {
        "theme": "10분 요리",
        Tier.beginner: "10분 안에 끝내는 간단한 요리",
        Tier.intermediate: "10분 안에 소스까지 만든 요리",
        Tier.advanced: "10분 안에 완성하는 정교한 요리",
    },
    {
        "theme": "건강한 요리",
        Tier.beginner: "채소를 곁들인 간단한 건강 요리",
        Tier.intermediate: "영양 균형을 맞춘 한 끼",
        Tier.advanced: "재료 손질부터 신경 쓴 건강 요리",
    },
]

# ---- shop seed: (name, category, value_label, value_krw, price_coins, validity_days) ----
SHOP_SEED = [
    ("커피 쿠폰", ShopCategory.cafe, "₩4,500 상당", 4500, 500, 90),
    ("음식 쿠폰", ShopCategory.food, "₩8,000 상당", 8000, 800, 90),
    ("편의점 쿠폰", ShopCategory.convenience, "₩3,000 상당", 3000, 300, 90),
    ("학식 식권", ShopCategory.food, "1회", None, 450, 90),
]
