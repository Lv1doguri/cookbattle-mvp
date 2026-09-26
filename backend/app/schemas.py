import datetime as dt
from typing import Annotated, List, Optional

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from .enums import Category, Tier, Tool

Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=16)]
Name40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


def _check_password_bytes(v: str) -> str:
    if len(v.encode("utf-8")) > 72:  # bcrypt only looks at the first 72 bytes
        raise ValueError("비밀번호가 너무 깁니다 (한글은 글자당 3바이트, 최대 72바이트)")
    return v


# ------------------------------------------------------------------ auth / me
class SignupIn(BaseModel):
    email: Optional[EmailStr] = None  # 회원가입 화면에 이메일 칸이 없어서 선택. 나중에 정보 수정에서 추가 가능
    nickname: Nickname
    password: str = Field(min_length=8, max_length=72)
    tier: Tier

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: str) -> str:
        return _check_password_bytes(v)


class LoginIn(BaseModel):
    # 이메일을 넣으세요. 이메일 없이 가입한 계정은 같은 칸에 닉네임을 넣으면 돼요('@'가 있으면 이메일로 봐요).
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(max_length=200)


class NicknameAvailableOut(BaseModel):
    available: bool


class ProfileUpdateIn(BaseModel):
    """정보 수정. 보낸 필드만 바뀌어요. password는 바꿀 때만 보내세요."""

    nickname: Optional[Nickname] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)
    tier: Optional[Tier] = None

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: Optional[str]) -> Optional[str]:
        return v if v is None else _check_password_bytes(v)


class Progress(BaseModel):
    """'Lv.2 · 보유 1,240P · 다음 레벨까지 6P → Lv.3' 를 그리는 데 필요한 값 전부."""

    level: int
    points: int  # 보유(교환에 쓸 수 있는) 포인트
    total_points: int  # 지금까지 모은 포인트. 레벨은 이 값 기준이라 교환해도 안 떨어져요
    level_start_points: int
    next_level_points: int
    points_to_next_level: int


class UserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: Optional[str]


class MeOut(UserBrief):
    email: Optional[str]
    tier: Tier
    tier_label: str
    pending_tier: Optional[Tier]  # 실력을 바꿨다면 "다음 대결부터" 적용될 값
    pending_tier_label: Optional[str]
    pending_tier_applies_at: Optional[dt.datetime]
    progress: Progress
    saved_recipe_count: int
    review_count: int


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeOut


class HistoryItem(BaseModel):
    battle_id: int
    entry_id: int
    title: str  # "계란 요리 대결"
    theme: str
    week_label: str  # "9월 3주차"
    tier: Tier
    tier_label: str
    status: str  # in_progress | ranked | void
    rank: Optional[int]  # 순위가 없으면 화면에는 "참가"


class MyReviewOut(BaseModel):
    id: int
    recipe_id: int
    recipe_name: str
    text: str
    created_at: dt.datetime


class HomeOut(BaseModel):
    me: MeOut
    cooking_count_this_month: int
    saved_amount_krw: int
    history: List[HistoryItem]  # 비어 있으면 "아직 참가한 대결이 없어요"
    reviews: List[MyReviewOut]
    review_total: int


# ------------------------------------------------------------------ recipes
class IngredientIn(BaseModel):
    name: Name40
    amount: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]] = None


class StepIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RecipeCreateIn(BaseModel):
    """대결 1등이 자기 레시피를 레시피 탭에 공유할 때."""

    name: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]] = None
    category: Category
    price: int = Field(ge=0, le=1_000_000)
    minutes: int = Field(ge=1, le=1440)
    difficulty: Tier
    tools: List[Tool] = Field(default_factory=list, max_length=4)
    ingredients: List[IngredientIn] = Field(min_length=1, max_length=30)
    steps: List[StepIn] = Field(min_length=1, max_length=30)


class RecipeCard(BaseModel):
    id: int
    name: str
    category: Category
    category_label: str
    price: int
    minutes: int
    difficulty: Tier
    difficulty_label: str
    win_label: Optional[str]  # "밥 요리 대결 1등"
    photo_url: Optional[str]
    saves: int
    is_saved: bool
    is_essential: bool  # "자취 필수"


class ToolOut(BaseModel):
    code: Tool
    label: str


class IngredientOut(BaseModel):
    name: str
    amount: Optional[str]


class StepOut(BaseModel):
    order: int
    text: str


class RecipeDetailOut(RecipeCard):
    author: UserBrief
    tools: List[ToolOut]
    ingredients: List[IngredientOut]
    steps: List[StepOut]
    comment_count: int
    created_at: dt.datetime


class RecipePage(BaseModel):
    total: int  # 필터에 맞는 전체 개수 ("{count}개 결과", "레시피 {count}개 보기")
    items: List[RecipeCard]
    has_more: bool


class SaveOut(BaseModel):
    saved: bool
    saves: int


class ReviewCreateIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ReviewOut(BaseModel):
    id: int
    recipe_id: int
    author: UserBrief
    text: str
    created_at: dt.datetime
    is_mine: bool


class ReviewPage(BaseModel):
    total: int
    items: List[ReviewOut]


# ------------------------------------------------------------------ battles
class PhotoOut(BaseModel):
    photo_id: int
    photo_url: str
    captured_at: dt.datetime  # 서버가 찍은 촬영(업로드) 시각
    expires_at: dt.datetime  # 이 시각까지 [제출]해야 해요. 지나면 다시 촬영


class JoinIn(BaseModel):
    photo_id: int
    dish_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class EntryOut(BaseModel):
    id: int
    battle_id: int
    dish_name: str
    description: str
    photo_url: str
    author: UserBrief
    vote_count: int
    created_at: dt.datetime
    # votable(투표) | mine(투표 불가) | voted(투표함) | vote_done(투표 완료) | unavailable(투표 기간/그룹 아님)
    state: str


class LastResultOut(BaseModel):
    battle_id: int
    title: str
    week_label: str
    status: str  # ranked | void
    joined: bool
    my_rank: Optional[int]


class BattleOut(BaseModel):
    id: int
    tier: Tier
    tier_label: str
    title: str  # "계란 요리 대결"
    theme: str  # "계란 요리"
    description: str
    week_label: str
    starts_at: dt.datetime
    ends_at: dt.datetime
    seconds_left: int
    days_left: int  # "남은 기간 3일"
    server_time: dt.datetime
    participants: int
    is_open: bool
    is_my_group: bool
    has_joined: bool
    can_join: bool
    my_entry: Optional[EntryOut]
    last_result: Optional[LastResultOut]


class EntryListOut(BaseModel):
    battle_id: int
    tier: Tier
    tier_label: str
    title: str
    participants: int
    is_open: bool
    can_vote: bool  # 내 그룹 대결이고 투표 기간이면 true
    has_voted: bool
    my_vote_entry_id: Optional[int]
    items: List[EntryOut]


class JoinOut(BaseModel):
    entry: EntryOut
    points_awarded: int
    points: int  # 참가 후 보유 포인트


class VoteOut(BaseModel):
    entry_id: int
    vote_count: int
    has_voted: bool


class ResultRow(BaseModel):
    rank: int
    entry_id: int
    user: UserBrief
    dish_name: str
    vote_count: int
    submitted_at: dt.datetime
    tie: Optional[str]  # first = "먼저 제출" · tied = "동점" · null = 동점 아님
    is_me: bool
    can_share_recipe: bool  # 1등이면 "레시피 공유 가능"


class ResultMe(BaseModel):
    joined: bool
    rank: Optional[int]
    participation_points: int
    rank_points: int  # "내 순위 2등 +4P" 의 4
    level_from: Optional[int]
    level_to: Optional[int]
    leveled_up: bool
    can_share_recipe: bool
    shared_recipe_id: Optional[int]


class ResultOut(BaseModel):
    battle_id: int
    tier: Tier
    tier_label: str
    title: str
    theme: str
    week_label: str
    participants: int
    status: str  # ranked | void (참가자 3명 미만 = 대결 무효)
    podium: List[ResultRow]
    top10: List[ResultRow]
    me: ResultMe


# ------------------------------------------------------------------ shop
class ShopItemOut(BaseModel):
    id: int
    name: str
    price_points: int
    required_level: int
    state: str  # available | insufficient_points | locked
    points_short: int  # insufficient_points일 때 "N P 더 필요해요"


class ShopOut(BaseModel):
    points: int
    level: int
    items: List[ShopItemOut]


class ExchangeOut(BaseModel):
    item_name: str
    points_spent: int
    points: int  # 남은 포인트
