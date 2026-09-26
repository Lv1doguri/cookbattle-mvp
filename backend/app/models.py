import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import relationship

from . import rules
from .database import Base
from .timeutil import today, utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)  # 로그인 ID
    nickname = Column(String, unique=True, index=True, nullable=False)  # 표시 이름 (중복 불가)
    password_hash = Column(String, nullable=False)
    skill = Column(String, nullable=False)  # rules.SKILLS 키 (low/mid/high) = 대결 그룹, 가입 후 변경 불가
    total_points = Column(Integer, default=0, nullable=False)  # 누적 포인트 → 레벨 계산용 (차감되지 않음)
    points = Column(Integer, default=0, nullable=False)  # 보유 포인트 → 상점에서 사용 (교환 시 차감)
    is_admin = Column(Boolean, default=False, nullable=False)
    invite_code = Column(String, unique=True, index=True, nullable=False)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tutorial_step = Column(Integer, default=0, nullable=False)  # 중간 이탈 시 이어보기용
    tutorial_completed = Column(Boolean, default=False, nullable=False)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)  # 올리면 기존 로그인 토큰 전부 무효
    created_at = Column(DateTime, default=utcnow)

    submissions = relationship("Submission", back_populates="user")

    @property
    def level(self) -> int:
        return rules.level_for(self.total_points or 0)


class Category(Base):
    """대결 카테고리 풀. 대결이 새로 열릴 때 여기서 랜덤으로 뽑힌다."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    kind = Column(String, default="league", nullable=False)  # league | fail (망한 요리 대회용 주제)
    is_active = Column(Boolean, default=True, nullable=False)


class Battle(Base):
    """대결 1회 (1주일). group마다 동시에 1개만 진행.
    - 리그 대결: group = low/mid/high (같은 실력끼리)
    - 망한 요리 대회: group = "fail" (리그 구분 없이 전체)
    기간: start_date ~ vote_start_date 전날 = 요리 기간 / vote_start_date ~ end_date = 투표 기간"""

    __tablename__ = "battles"

    id = Column(Integer, primary_key=True, index=True)
    group = Column(String, nullable=False, index=True)  # low/mid/high 또는 fail
    kind = Column(String, default="league", nullable=False)  # league | fail
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    vote_start_date = Column(Date, nullable=True)  # 투표 시작일 (null이면 start + COOKING_DAYS)
    end_date = Column(Date, nullable=False)
    verification_keyword = Column(String, nullable=False)  # 인증샷에 같이 찍는 단어
    is_closed = Column(Boolean, default=False, nullable=False)
    is_void = Column(Boolean, default=False, nullable=False)  # 참가자 부족으로 무효
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    category = relationship("Category")
    submissions = relationship("Submission", back_populates="battle")

    @property
    def voting_starts(self):
        return self.vote_start_date or (self.start_date + dt.timedelta(days=rules.COOKING_DAYS))

    @property
    def phase(self) -> str:
        """cooking(사진 올리기) → voting(참가자 투표) → closed"""
        if self.is_closed:
            return "closed"
        return "cooking" if today() < self.voting_starts else "voting"


# 그룹당 진행 중(is_closed=0) 대결은 DB 차원에서도 1개만 (동시 요청으로 대결이 2개 생기는 것 방지)
Index("uq_open_battle_per_group", Battle.group, unique=True, sqlite_where=Battle.is_closed == false())


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("battle_id", "user_id", name="uq_one_entry_per_battle"),)

    id = Column(Integer, primary_key=True, index=True)
    battle_id = Column(Integer, ForeignKey("battles.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)  # 요리명
    description = Column(Text, default="")
    ingredient_cost = Column(Integer, nullable=True)  # 재료비(원), 절약 식비 계산용 (선택)
    is_hidden = Column(Boolean, default=False, nullable=False)
    ai_status = Column(String, nullable=True)  # passed | failed(advisory) | skipped | error
    ai_result = Column(JSON, nullable=True)  # AI 판별 상세
    created_at = Column(DateTime, default=utcnow)

    battle = relationship("Battle", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    images = relationship(
        "SubmissionImage",
        back_populates="submission",
        order_by="SubmissionImage.position",
        cascade="all, delete-orphan",
    )


class SubmissionImage(Base):
    __tablename__ = "submission_images"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    path = Column(String, nullable=False)
    position = Column(Integer, default=0, nullable=False)
    shot_type = Column(String, nullable=True)  # rules.SHOT_TYPES 키 (front/keyword/top/...)
    phash = Column(String, nullable=True, index=True)  # 지각 해시 → 같은 사진 재사용 차단
    taken_at = Column(DateTime, nullable=True)  # EXIF 촬영 시각 (없으면 null)

    submission = relationship("Submission", back_populates="images")


class Vote(Base):
    """1인 1표 (대결당)."""

    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("battle_id", "voter_id", name="uq_one_vote_per_battle"),)

    id = Column(Integer, primary_key=True, index=True)
    battle_id = Column(Integer, ForeignKey("battles.id"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Comment(Base):
    """대결 작품 평가: 댓글 + 별점(1~5). 한 사람이 한 작품에 1개 (수정 가능)."""

    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("submission_id", "user_id", name="uq_one_review_per_submission"),)

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1~5 (이전 버전 댓글은 null)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, nullable=True)

    user = relationship("User")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("submission_id", "reporter_id", name="uq_one_report_per_user"),)

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


class PointLog(Base):
    """포인트 적립 기록. (user, reason, ref) 유니크 → 같은 보상 중복 지급 없음."""

    __tablename__ = "point_logs"
    __table_args__ = (UniqueConstraint("user_id", "reason", "ref", name="uq_point_once"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)  # participation / rank / streak / recipe_complete / invite / invited
    ref = Column(String, nullable=False)  # "battle:3", "recipe:5", "week:2026-39", "user:7"
    memo = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    ingredients = Column(JSON, default=list)  # [{"name": "김치", "amount": "1컵", "price": 1500}]
    steps = Column(JSON, default=list)  # ["김치를 잘게 썬다", ...]
    estimated_cost = Column(Integer, nullable=True)  # 재료별 가격 합계 (자동 계산)
    cook_minutes = Column(Integer, nullable=True)  # 조리 시간(분)
    difficulty = Column(String, nullable=True)  # rules.RECIPE_DIFFICULTIES 키 (easy/normal/hard)
    food_type = Column(String, nullable=True, index=True)  # rules.RECIPE_FOOD_TYPES 키
    tags = Column(JSON, default=list)  # rules.RECIPE_TAGS 중에서 (예: ["자취 필수"])
    tools = Column(String, default="")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, unique=True)
    is_official = Column(Boolean, default=False, nullable=False)
    image_path = Column(String, nullable=True)  # 사진 1장
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, nullable=True)

    author = relationship("User")
    source_submission = relationship("Submission")


class RecipeSave(Base):
    __tablename__ = "recipe_saves"
    __table_args__ = (UniqueConstraint("recipe_id", "user_id", name="uq_save_once"),)

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)

    recipe = relationship("Recipe")


class RecipeView(Base):
    """최근 본 레시피 (사용자·레시피당 1행, 볼 때마다 시각 갱신)."""

    __tablename__ = "recipe_views"
    __table_args__ = (UniqueConstraint("recipe_id", "user_id", name="uq_view_row"),)

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=utcnow)

    recipe = relationship("Recipe")


class RecipeReview(Base):
    """레시피 후기(댓글)."""

    __tablename__ = "recipe_reviews"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User")
    recipe = relationship("Recipe")


class RecipeCompletion(Base):
    """레시피 따라하기 완료 인증."""

    __tablename__ = "recipe_completions"
    __table_args__ = (UniqueConstraint("recipe_id", "user_id", name="uq_complete_once"),)

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    recipe = relationship("Recipe")


class ShopItem(Base):
    __tablename__ = "shop_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    price = Column(Integer, nullable=False)  # 필요 포인트
    min_level = Column(Integer, default=1, nullable=False)  # 레벨 제한
    stock = Column(Integer, nullable=True)  # null = 무제한
    is_active = Column(Boolean, default=True, nullable=False)


class Exchange(Base):
    """상점 교환 내역 (MVP: 실제 발송 없이 기록만)."""

    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("shop_items.id"), nullable=False)
    price = Column(Integer, nullable=False)  # 교환 당시 가격
    created_at = Column(DateTime, default=utcnow)

    item = relationship("ShopItem")
    user = relationship("User")


class Friendship(Base):
    """친구 관계. 요청(pending) → 수락(accepted). 거절·취소·삭제하면 행이 지워져 다시 요청 가능.
    한 쌍의 사용자 사이에는 방향과 상관없이 1행만 존재한다 (서비스 로직에서 보장)."""

    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friend_pair"),)

    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    addressee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")  # pending | accepted
    created_at = Column(DateTime, default=utcnow)
    responded_at = Column(DateTime, nullable=True)

    requester = relationship("User", foreign_keys=[requester_id])
    addressee = relationship("User", foreign_keys=[addressee_id])
