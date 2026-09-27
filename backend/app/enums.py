import enum


class Tier(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


TIER_LABEL = {
    Tier.beginner: "초급",
    Tier.intermediate: "중급",
    Tier.advanced: "상급",
}


class Category(str, enum.Enum):
    rice = "rice"
    noodle = "noodle"
    pasta = "pasta"
    meat = "meat"
    soup = "soup"
    side = "side"
    healthy = "healthy"
    dessert = "dessert"


CATEGORY_LABEL = {
    Category.rice: "밥",
    Category.noodle: "면",
    Category.pasta: "파스타",
    Category.meat: "고기",
    Category.soup: "국·찌개",
    Category.side: "반찬",
    Category.healthy: "건강식",
    Category.dessert: "디저트",
}


class Tool(str, enum.Enum):
    microwave = "microwave"
    pan = "pan"
    airfryer = "airfryer"
    rice_cooker = "rice_cooker"


TOOL_LABEL = {
    Tool.microwave: "전자레인지만",
    Tool.pan: "프라이팬 하나",
    Tool.airfryer: "에어프라이어",
    Tool.rice_cooker: "밥솥",
}


class Budget(str, enum.Enum):
    """레시피 필터 '예산'. under_5000: <=5,000 · between: 5,001~10,000 · over_10000: >10,000"""

    under_5000 = "under_5000"
    between_5000_10000 = "5000_to_10000"
    over_10000 = "over_10000"


class CookTime(str, enum.Enum):
    """레시피 필터 '조리 시간'. le_10/le_15/le_30 = N분 이하, ge_60 = 1시간 이상"""

    le_10 = "le_10"
    le_15 = "le_15"
    le_30 = "le_30"
    ge_60 = "ge_60"


class BattleKind(str, enum.Enum):
    """daily: 실력 그룹별 주간 대결('오늘의 대결'). theme: 전체 공통 테마 대결(예: 망한 요리 대회)."""

    daily = "daily"
    theme = "theme"


class BattlePhase(str, enum.Enum):
    """cooking(참가 가능) -> voting(대회 종료 후 24시간, 투표만 가능) -> closed(집계 완료)."""

    cooking = "cooking"
    voting = "voting"
    closed = "closed"
