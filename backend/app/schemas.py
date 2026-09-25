import datetime as dt
from typing import Annotated, List, Optional

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from .enums import Category, ShopCategory, Tier

Name40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


# ------------------------------------------------------------------ users / auth
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nickname: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]] = None

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:  # bcrypt only looks at the first 72 bytes
            raise ValueError("비밀번호가 너무 깁니다 (한글은 글자당 3바이트, 최대 72바이트)")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class TierIn(BaseModel):
    tier: Tier


class ProfileUpdateIn(BaseModel):
    nickname: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]] = None
    bio: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]] = None
    handle: Optional[str] = Field(default=None, pattern=r"^[a-z0-9_.]{3,20}$")


class UserBrief(BaseModel):
    id: int
    nickname: str
    handle: str
    tier: Optional[Tier]
    tier_label: Optional[str]


class Progress(BaseModel):
    """Everything the level bar needs: '중급 Lv.3   1,250 / 1,500'."""

    tier: Optional[Tier]
    tier_label: Optional[str]
    level: int
    xp: int
    level_start_xp: int
    next_level_xp: int
    xp_to_next_level: int


class MeOut(UserBrief):
    email: str
    bio: str
    needs_tier_selection: bool
    coins: int
    progress: Progress
    follower_count: int
    following_count: int
    post_count: int


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeOut


class UserProfileOut(UserBrief):
    bio: str
    level: int
    follower_count: int
    following_count: int
    post_count: int
    is_following: bool
    is_me: bool


class FollowOut(BaseModel):
    following: bool
    follower_count: int


# ------------------------------------------------------------------ photos
class PhotoOut(BaseModel):
    photo_id: int
    photo_url: str
    captured_at: dt.datetime
    expires_at: dt.datetime


# ------------------------------------------------------------------ posts / recipes
class IngredientIn(BaseModel):
    name: Name40
    amount: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]] = None


class StepIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class PostCreateIn(BaseModel):
    photo_id: int
    caption: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    ingredients: List[IngredientIn] = Field(min_length=1, max_length=30)
    steps: List[StepIn] = Field(min_length=1, max_length=30)
    cost_krw: int = Field(ge=0, le=1_000_000)
    cook_minutes: int = Field(ge=1, le=1440)
    difficulty: Tier
    category: Optional[Category] = None
    battle_id: Optional[int] = None


class RecipeSummary(BaseModel):
    title: str
    cost_krw: int
    cook_minutes: int
    difficulty: Tier
    difficulty_label: str
    ingredient_count: int


class PostOut(BaseModel):
    id: int
    caption: str
    photo_url: str
    captured_at: dt.datetime
    created_at: dt.datetime
    category: Optional[Category]
    category_label: Optional[str]
    author: UserBrief
    recipe: RecipeSummary
    like_count: int
    comment_count: int
    save_count: int
    is_liked: bool
    is_saved: bool
    is_following_author: bool
    is_mine: bool
    battle_id: Optional[int]


class PostDetailOut(PostOut):
    author_follower_count: int


class IngredientOut(BaseModel):
    name: str
    amount: Optional[str]


class StepOut(BaseModel):
    order: int
    text: str


class RecipeDetailOut(PostOut):
    ingredients: List[IngredientOut]
    steps: List[StepOut]
    rating_avg: Optional[float]
    rating_count: int
    my_rating: Optional[int]


class PostPage(BaseModel):
    items: List[PostOut]
    has_more: bool


class RewardOut(BaseModel):
    xp: int
    coins: int
    is_battle_entry: bool
    daily_limit_reached: bool
    leveled_up: bool


class PostCreatedOut(BaseModel):
    post: PostDetailOut
    reward: RewardOut
    progress: Progress
    coins: int


class LikeOut(BaseModel):
    liked: bool
    like_count: int


class SaveOut(BaseModel):
    saved: bool
    save_count: int


class RatingIn(BaseModel):
    score: int = Field(ge=1, le=5)


class RatingOut(BaseModel):
    rating_avg: Optional[float]
    rating_count: int
    my_rating: Optional[int]


class RecipeWinnerOut(BaseModel):
    tier: Tier
    tier_label: str
    battle_date: dt.date
    recipe: PostOut


# ------------------------------------------------------------------ comments
class CommentCreateIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    parent_id: Optional[int] = None


class CommentOut(BaseModel):
    id: int
    post_id: int
    parent_id: Optional[int]
    author: UserBrief
    text: str
    created_at: dt.datetime
    like_count: int
    is_liked: bool
    is_mine: bool


class CommentPage(BaseModel):
    items: List[CommentOut]
    total: int


class CommentLikeOut(BaseModel):
    liked: bool
    like_count: int


# ------------------------------------------------------------------ battles
class WeeklyThemeOut(BaseModel):
    weekday: str
    theme: str
    is_today: bool


class MyEntryOut(BaseModel):
    post_id: int
    xp: int
    rank: int


class BattleOut(BaseModel):
    id: int
    date: dt.date
    tier: Tier
    tier_label: str
    theme: str
    description: str
    reward_xp: int
    reward_coins: int
    starts_at: dt.datetime
    ends_at: dt.datetime
    seconds_left: int
    server_time: dt.datetime
    participants: int
    is_my_tier: bool
    can_join: bool
    my_entry: Optional[MyEntryOut]
    weekly_challenge: List[WeeklyThemeOut]


class LeaderboardEntry(BaseModel):
    rank: int
    user: UserBrief
    xp: int
    post_id: int
    is_me: bool


class LeaderboardMe(BaseModel):
    rank: int
    xp: int
    xp_to_next_rank: int


class LeaderboardOut(BaseModel):
    battle_id: int
    tier: Tier
    tier_label: str
    theme: str
    participants: int
    entries: List[LeaderboardEntry]
    me: Optional[LeaderboardMe]


# ------------------------------------------------------------------ shop / coupons
class ShopItemOut(BaseModel):
    id: int
    name: str
    category: ShopCategory
    category_label: str
    value_label: str
    value_krw: Optional[int]
    price_coins: int
    validity_days: int


class ShopOut(BaseModel):
    coins: int
    available_coupon_count: int
    items: List[ShopItemOut]


class CouponOut(BaseModel):
    id: int
    name: str
    value_label: str
    value_krw: Optional[int]
    code: str
    status: str  # available | used | expired
    is_new: bool
    created_at: dt.datetime
    expires_at: dt.datetime
    used_at: Optional[dt.datetime]


class PurchaseOut(BaseModel):
    coupon: CouponOut
    coins: int


class CouponListOut(BaseModel):
    available_count: int
    used_count: int
    expired_count: int
    items: List[CouponOut]
