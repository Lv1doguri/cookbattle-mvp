import datetime as dt
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _password_rule(v: str) -> str:
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("영문과 숫자를 모두 포함해 주세요")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("너무 길어요")
    return v


# ---------- auth / user ----------
class SignupRequest(BaseModel):
    email: EmailStr
    nickname: str = Field(min_length=2, max_length=12)
    password: str = Field(min_length=8, max_length=72, description="8자 이상, 영문+숫자")

    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        return _password_rule(v)
    skill: str  # "low" | "mid" | "high"
    invite_code: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    id: int
    email: str
    nickname: str
    skill: str
    skill_label: str
    level: int
    total_points: int
    points: int
    next_level_points: int
    points_to_next_level: int
    level_progress: float
    is_admin: bool
    invite_code: str
    tutorial_step: int
    tutorial_completed: bool
    notifications_enabled: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=2, max_length=12)
    current_password: Optional[str] = Field(default=None, max_length=200)
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v):
        return None if v is None else _password_rule(v)
    notifications_enabled: Optional[bool] = None


class TutorialUpdate(BaseModel):
    step: Optional[int] = Field(default=None, ge=0)
    completed: Optional[bool] = None


class PointLogOut(BaseModel):
    points: int
    reason: str
    ref: str
    memo: str
    created_at: dt.datetime


# ---------- battle ----------
class CategoryOut(BaseModel):
    id: int
    name: str
    description: str


class BattleOut(BaseModel):
    id: int
    kind: str  # league | fail
    kind_label: str  # "리그 대결" / "망한 요리 대회"
    group: str  # low/mid/high 또는 fail
    group_label: str  # "하"/"중"/"상" 또는 "전체"
    category: CategoryOut
    start_date: dt.date
    cooking_end_date: dt.date  # 요리(사진 올리기) 마지막 날
    vote_start_date: dt.date  # 투표 시작일
    end_date: dt.date  # 투표 마지막 날 = 대결 종료
    phase: str  # cooking | voting | closed
    phase_label: str  # "요리 기간" / "투표 기간" / "종료"
    phase_days_left: int  # 지금 단계 남은 날 (마지막 날 0)
    days_left: int  # 대결 종료까지 남은 날
    verification_keyword: str
    is_closed: bool
    is_void: bool
    submission_count: int
    has_submitted: bool
    has_voted: bool
    can_submit: bool  # 지금 참가 가능
    can_vote: bool  # 지금 투표 가능 (투표 기간 + 참가자 + 아직 안 함)
    vote_block_reason: Optional[str]  # 투표 불가 이유 (버튼 아래 안내 문구)
    is_my_group: bool


class SubmissionImageOut(BaseModel):
    url: str
    shot_type: Optional[str]
    shot_label: str
    time_verified: bool  # EXIF 촬영 시각이 있어 대결 기간 안임이 확인됨


class AICheckOut(BaseModel):
    status: str  # passed | failed | skipped | error
    summary: str
    warnings: list[str]  # advisory 모드에서 거절하지 않고 남긴 문제점


class SubmissionOut(BaseModel):
    id: int
    battle_id: int
    user_id: int
    nickname: str
    user_level: int
    title: str
    description: str
    ingredient_cost: Optional[int]
    image_url: str
    image_urls: list[str]
    images: list[SubmissionImageOut]  # 구도별 사진
    photo_verified: bool  # 모든 사진의 촬영 시각이 확인됨 → "촬영 인증" 배지
    ai_verified: bool  # 이미지 인식 AI 검사 통과 → "AI 인증" 배지
    ai_check: Optional[AICheckOut]
    created_at: dt.datetime
    vote_count: Optional[int]  # HIDE_VOTES_UNTIL_CLOSED=True면 마감 전 null
    has_voted: bool  # 내가 이 작품에 투표했는지
    is_mine: bool
    is_hidden: bool
    comment_count: int
    rating_avg: Optional[float]  # 별점 평균 (평가 없으면 null)
    rating_count: int


class SubmitResult(BaseModel):
    submission: SubmissionOut
    points_earned: int
    level: int
    leveled_up: bool


class VoteResponse(BaseModel):
    submission_id: int
    vote_count: Optional[int]


class ResultEntry(BaseModel):
    submission_id: int
    user_id: int
    nickname: str
    title: str
    image_url: str
    vote_count: int
    rank: int
    rank_points: int
    recipe_id: Optional[int] = None  # 이 작품으로 공유된 레시피 (TOP 목록의 '레시피 공유' 표시·이동용)


class MyResult(BaseModel):
    submission_id: Optional[int]
    rank: Optional[int]
    points_earned: int
    level_before: Optional[int]
    level_after: Optional[int]
    leveled_up: bool
    can_share_recipe: bool


class BattleResults(BaseModel):
    battle: BattleOut
    is_void: bool
    podium: list[ResultEntry]  # 1~3등
    entries: list[ResultEntry]  # 전체 순위
    my_result: Optional[MyResult]


# ---------- feedback ----------
class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class CommentOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    content: str
    created_at: dt.datetime
    is_mine: bool


class BattleCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    rating: int = Field(ge=1, le=5, description="별점 1~5")


class BattleCommentUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1, max_length=500)
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class BattleCommentOut(BaseModel):
    id: int
    submission_id: int
    user_id: int
    nickname: str
    content: str
    rating: Optional[int]
    created_at: dt.datetime  # UTC
    created_at_display: str  # 한국 시간 표시용 "2026-09-25 14:03"
    is_edited: bool
    is_mine: bool


class RatingSummary(BaseModel):
    average: Optional[float]  # 소수 첫째 자리, 평가 없으면 null
    count: int
    distribution: dict  # {"5": 3, "4": 1, "3": 0, "2": 0, "1": 0}


class BattleCommentList(BaseModel):
    summary: RatingSummary
    comments: list[BattleCommentOut]


class ReportCreate(BaseModel):
    reason: str = Field(default="", max_length=200)


# ---------- recipe ----------
class Ingredient(BaseModel):
    name: str = Field(min_length=1, max_length=30)  # "김치"
    amount: str = Field(default="", max_length=20)  # "1컵"
    price: Optional[int] = Field(default=None, ge=0, le=1_000_000)  # 원 (입력하면 예상 재료비 자동 계산)


def _clean_steps(v):
    v = [s.strip() for s in v if s and s.strip()]
    if not v:
        raise ValueError("조리 과정을 1개 이상 입력해 주세요")
    if any(len(s) > 300 for s in v):
        raise ValueError("조리 과정 한 단계는 300자 이내로 써 주세요")
    return v


def _check_choice(v, options: dict, what: str):
    if v is not None and v not in options:
        raise ValueError(f"{what}는 {', '.join(options)} 중 하나예요")
    return v


def _clean_tags(v):
    from .rules import RECIPE_TAGS
    v = list(dict.fromkeys(t.strip() for t in (v or []) if t and t.strip()))
    bad = [t for t in v if t not in RECIPE_TAGS]
    if bad:
        raise ValueError(f"사용할 수 없는 태그예요: {', '.join(bad)}")
    return v


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=1000)
    ingredients: list[Ingredient] = Field(min_length=1, max_length=30)
    steps: list[str] = Field(min_length=1, max_length=30)
    cook_minutes: int = Field(ge=1, le=600, description="조리 시간(분)")
    difficulty: str = Field(description="easy(초급) / normal(중급) / hard(상급)")
    food_type: str = Field(description="rice/noodle/pasta/meat/soup/side/healthy/dessert")
    tags: list[str] = Field(default=[], max_length=6, description="자취 필수, 전자레인지, 원팬, 야식, 도시락, 다이어트")
    tools: str = Field(default="", max_length=100)

    @field_validator("steps")
    @classmethod
    def check_steps(cls, v):
        return _clean_steps(v)

    @field_validator("difficulty")
    @classmethod
    def check_difficulty(cls, v):
        from .rules import RECIPE_DIFFICULTIES
        return _check_choice(v, RECIPE_DIFFICULTIES, "난이도")

    @field_validator("food_type")
    @classmethod
    def check_food_type(cls, v):
        from .rules import RECIPE_FOOD_TYPES
        return _check_choice(v, RECIPE_FOOD_TYPES, "종류")

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v):
        return _clean_tags(v)


class RecipeUpdate(BaseModel):
    """레시피 수정 — 바꿀 항목만 보내면 된다."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=1000)
    ingredients: Optional[list[Ingredient]] = Field(default=None, min_length=1, max_length=30)
    steps: Optional[list[str]] = Field(default=None, min_length=1, max_length=30)
    cook_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    difficulty: Optional[str] = None
    food_type: Optional[str] = None
    tags: Optional[list[str]] = Field(default=None, max_length=6)
    tools: Optional[str] = Field(default=None, max_length=100)

    @field_validator("steps")
    @classmethod
    def check_steps(cls, v):
        return None if v is None else _clean_steps(v)

    @field_validator("difficulty")
    @classmethod
    def check_difficulty(cls, v):
        from .rules import RECIPE_DIFFICULTIES
        return _check_choice(v, RECIPE_DIFFICULTIES, "난이도")

    @field_validator("food_type")
    @classmethod
    def check_food_type(cls, v):
        from .rules import RECIPE_FOOD_TYPES
        return _check_choice(v, RECIPE_FOOD_TYPES, "종류")

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v):
        return None if v is None else _clean_tags(v)


class RecipeOut(BaseModel):
    id: int
    title: str
    description: str
    ingredients: list[dict]  # [{"name", "amount", "price"}]
    steps: list[str]
    estimated_cost: Optional[int]  # 예상 재료비 (재료 가격 합계)
    cook_minutes: Optional[int]
    difficulty: Optional[str]
    difficulty_label: str  # 초급/중급/상급
    food_type: Optional[str]
    food_type_label: str  # 밥/면/...
    tags: list[str]
    tools: str
    source: str  # official(공식) | winner(대결 우승) | user(사용자)
    badge: Optional[str]  # "밥 요리 대결 1등" / "요리왕 공식"
    author_id: Optional[int]
    author_nickname: Optional[str]
    is_official: bool
    is_mine: bool
    source_submission_id: Optional[int]
    image_url: Optional[str]
    save_count: int
    review_count: int
    completion_count: int
    saved_by_me: bool
    completed_by_me: bool
    matched_ingredients: Optional[list[str]] = None  # '재료로 찾기'일 때만: 가진 재료 중 쓰이는 것
    missing_ingredients: Optional[list[str]] = None  # '재료로 찾기'일 때만: 더 필요한 재료
    created_at: dt.datetime


class RecipeList(BaseModel):
    total: int  # 필터에 맞는 전체 개수 ("8개 결과")
    items: list[RecipeOut]


class ReviewOut(BaseModel):
    id: int
    recipe_id: int
    recipe_title: str
    user_id: int
    nickname: str
    content: str
    created_at: dt.datetime
    is_mine: bool


# ---------- shop ----------
class ShopItemOut(BaseModel):
    id: int
    name: str
    description: str
    price: int
    min_level: int
    stock: Optional[int]
    can_exchange: bool
    blocked_reason: Optional[str]  # "N포인트 더 필요해요" / "N레벨부터 교환 가능" / "품절"


class ShopItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)
    price: int = Field(ge=1)
    min_level: int = Field(default=1, ge=1)
    stock: Optional[int] = Field(default=None, ge=0)


class ExchangeOut(BaseModel):
    id: int
    item_id: int
    item_name: str
    price: int
    created_at: dt.datetime
    points_left: Optional[int] = None


# ---------- admin ----------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    description: str = Field(default="", max_length=200)
    kind: str = Field(default="league", pattern="^(league|fail)$")  # fail = 망한 요리 대회 주제


class PhaseChange(BaseModel):
    phase: str = Field(pattern="^(cooking|voting)$")


class StartBattleRequest(BaseModel):
    group: str
    category_id: Optional[int] = None  # 비우면 랜덤


# ---------- friends ----------
class UserBrief(BaseModel):
    user_id: int
    nickname: str
    level: int
    skill: str
    skill_label: str


class UserSearchOut(UserBrief):
    relation: str  # self | friend | request_sent | request_received | none
    request_id: Optional[int]  # 요청 수락/거절/취소에 쓰는 id


class FriendRequestCreate(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=30)  # 닉네임 또는
    user_id: Optional[int] = None  # user_id 중 하나


class FriendRequestOut(BaseModel):
    id: int
    from_user: UserBrief
    to_user: UserBrief
    created_at: dt.datetime
    created_at_display: str


class FriendOut(UserBrief):
    total_points: int
    friends_since: Optional[dt.datetime]
    last_cooked_at: Optional[str]  # 마지막 대결 참가 (한국 시간 표시용), 없으면 null
    battle_count: int


class RankingEntry(UserBrief):
    rank: int
    total_points: int
    win_count: int
    is_me: bool
