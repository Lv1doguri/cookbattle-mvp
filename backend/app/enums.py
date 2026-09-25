import enum


class Tier(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


TIER_LABEL = {
    Tier.beginner: "초급",
    Tier.intermediate: "중급",
    Tier.advanced: "고급",
}


class Category(str, enum.Enum):
    rice = "rice"
    noodle = "noodle"
    pasta = "pasta"
    meat = "meat"
    healthy = "healthy"
    dessert = "dessert"


CATEGORY_LABEL = {
    Category.rice: "밥",
    Category.noodle: "면",
    Category.pasta: "파스타",
    Category.meat: "고기",
    Category.healthy: "건강식",
    Category.dessert: "디저트",
}


class ShopCategory(str, enum.Enum):
    cafe = "cafe"
    food = "food"
    convenience = "convenience"


SHOP_CATEGORY_LABEL = {
    ShopCategory.cafe: "카페",
    ShopCategory.food: "음식",
    ShopCategory.convenience: "편의점",
}
