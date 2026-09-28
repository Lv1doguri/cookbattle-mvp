import datetime as dt
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from .enums import BattleKind, BattlePhase, Category, Tier, Tool

Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=16)]
Name40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


def _check_password_bytes(v: str) -> str:
    if len(v.encode("utf-8")) > 72:  # bcrypt only looks at the first 72 bytes
        raise ValueError("비밀번호가 너무 깁니다 (한글은 글자당 3바이트, 최대 72바이트)")
    return v


# ------------------------------------------------------------------ auth / me
class SignupIn(BaseModel):
    email: EmailStr
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


class GoogleAuthIn(BaseModel):
    id_token: str
    # 이 구글 계정으로 처음 가입하는 경우에만 쓰여요. 디자인엔 구글 가입 시 실력 선택 화면이 없어서,
    # 안 보내면 초급으로 시작해요(정보 수정에서 바꿀 수 있어요) — API_CONTRACT.md 참고.
    tier: Optional[Tier] = None


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
    tier: Optional[Tier]  # 테마 대결(전체 공통)이면 null
    tier_label: Optional[str]
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
    photo_id: int  # 기본(정면) 사진
    angle_photo_id: int  # 대결이 요구하는 구도로 찍은 추가 사진 (BattleOut.required_angle 참고)
    dish_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class EntryOut(BaseModel):
    id: int
    battle_id: int
    dish_name: str
    description: str
    photo_url: str
    angle_photo_url: Optional[str] = None  # 이 기능 이전에 만들어진 출품작은 null
    author: UserBrief
    vote_count: int
    created_at: dt.datetime
    notify_on_close: bool  # "대회 종료 시 알림 받기"를 눌렀는지
    # votable(투표) | mine(투표 불가) | voted(투표함) | vote_done(투표 완료) | unavailable(투표 기간/그룹 아님)
    state: str
    comment_count: int = 0
    rating_avg: Optional[float] = None  # 평가 없으면 null
    rating_count: int = 0


class EntryCommentCreateIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    visual_rating: int = Field(ge=1, le=5)  # 비주얼
    value_rating: int = Field(ge=1, le=5)  # 가성비


class EntryCommentUpdateIn(BaseModel):
    text: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]] = None
    visual_rating: Optional[int] = Field(default=None, ge=1, le=5)
    value_rating: Optional[int] = Field(default=None, ge=1, le=5)


class EntryCommentOut(BaseModel):
    id: int
    entry_id: int
    author: UserBrief
    text: str
    visual_rating: int
    value_rating: int
    overall_rating: float  # 두 항목 평균, 소수 첫째 자리 반올림
    created_at: dt.datetime
    is_edited: bool
    is_mine: bool


class RatingSummaryOut(BaseModel):
    average: Optional[float]  # overall_rating 평균
    visual_average: Optional[float]
    value_average: Optional[float]
    count: int
    distribution: dict  # overall_rating을 반올림한 {"5": n, "4": n, "3": n, "2": n, "1": n}


class EntryCommentPage(BaseModel):
    summary: RatingSummaryOut
    items: List[EntryCommentOut]


class LastResultOut(BaseModel):
    battle_id: int
    title: str
    week_label: str
    status: str  # ranked | void
    joined: bool
    my_rank: Optional[int]


class BattleOut(BaseModel):
    id: int
    kind: BattleKind
    tier: Optional[Tier]  # kind=theme이면 null (전체 공통)
    tier_label: Optional[str]
    title: str  # "계란 요리 대결"
    theme: str  # "계란 요리"
    description: str
    week_label: str
    required_angle: str  # content.ANGLE_BY_ID의 id (예: "top")
    required_angle_label: str  # "위에서 내려다본 모습"
    required_angle_instruction: str  # 카메라 화면에 그대로 보여줄 안내 문구
    starts_at: dt.datetime
    ends_at: dt.datetime  # 요리(참가) 기간 마감
    voting_ends_at: dt.datetime  # 투표 마감 (ends_at + 24시간)
    phase: BattlePhase
    seconds_left: int  # 지금 단계(요리 또는 투표)가 끝날 때까지 남은 초
    days_left: int  # "남은 기간 3일" (요리 기간 기준)
    server_time: dt.datetime
    participants: int
    is_open: bool  # 요리 기간이 아직 안 끝났는지 (참가 가능 여부의 기준)
    is_my_group: bool
    has_joined: bool
    can_join: bool
    my_entry: Optional[EntryOut]
    last_result: Optional[LastResultOut]


class EntryListOut(BaseModel):
    battle_id: int
    kind: BattleKind
    tier: Optional[Tier]
    tier_label: Optional[str]
    title: str
    participants: int
    phase: BattlePhase
    can_vote: bool  # 내 그룹(또는 테마) 대결이고 투표 기간(대회 종료 후 24시간)이면 true
    has_voted: bool
    my_vote_entry_id: Optional[int]
    items: List[EntryOut]


class VotingCardOut(BaseModel):
    """대결 홈의 '지난 대회 투표하기' 카드. 투표 가능한 지난 대회가 없으면 null이에요."""

    battle_id: int
    kind: BattleKind
    title: str
    group_label: Optional[str]  # tier_label, 테마 대결이면 null
    participants: int
    hours_left: int  # 투표 마감까지 남은 시간(반올림)
    has_voted: bool


class BattleHomeOut(BaseModel):
    """대결 홈 화면 한 번에: 내 그룹의 오늘의 대결 + 테마 대결 + 지난 대회 투표 카드."""

    daily: BattleOut
    theme: BattleOut
    voting: Optional[VotingCardOut]


class JoinOut(BaseModel):
    entry: EntryOut
    points_awarded: int
    points: int  # 참가 후 보유 포인트


class VoteOut(BaseModel):
    entry_id: int
    vote_count: int
    has_voted: bool
    points_awarded: int  # 투표하면 +1P


class NotifyOut(BaseModel):
    """MVP: 실제 알림 발송은 없고, 원하는지 여부만 저장돼요."""

    notify_on_close: bool


class ResultRow(BaseModel):
    rank: int
    entry_id: int
    user: UserBrief
    dish_name: str
    vote_count: int
    submitted_at: dt.datetime
    tie: Optional[str]  # first = "먼저 제출" · tied = "동점" · null = 동점 아님
    is_me: bool
    is_winner: bool  # 1등 행의 "레시피 공유" 표시(누가 봐도 true)
    can_share_recipe: bool  # 내가 1등이고 아직 공유 안 했을 때만 true → 이때만 누를 수 있는 [레시피 공유] 버튼


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
    kind: BattleKind
    tier: Optional[Tier]
    tier_label: Optional[str]
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


# ------------------------------------------------------------------ admin (demo/ops tools)
class AdminPhaseIn(BaseModel):
    phase: Literal["cooking", "voting"]


class AdminBattleOut(BaseModel):
    id: int
    kind: BattleKind
    phase: BattlePhase
    ends_at: dt.datetime
    voting_ends_at: dt.datetime
    finalized_at: Optional[dt.datetime]
    is_void: bool


class AdminCloseOut(BaseModel):
    battle_id: int
    finalized: bool
    is_void: bool
    participants: int


class AdminShopItemCreateIn(BaseModel):
    name: Name40
    price_points: int = Field(ge=1)
    required_level: int = Field(default=1, ge=1)
    monthly_limit: Optional[int] = Field(default=None, ge=0)
