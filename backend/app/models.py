import datetime as dt
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from . import clock
from .database import Base
from .enums import BattleKind, Category, Tier, Tool


class UTCDateTime(TypeDecorator):
    """SQLite drops tzinfo; this stores naive UTC and always hands back aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime not allowed; use timezone-aware UTC")
        return value.astimezone(dt.timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=dt.timezone.utc)


def _now() -> dt.datetime:
    return clock.utcnow()  # looked up at call time so tests can patch clock.utcnow


def _enum(enum_cls):
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("points >= 0", name="ck_users_points_nonneg"),
        CheckConstraint("total_points >= points", name="ck_users_total_ge_balance"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # 회원가입 화면에 이메일 칸이 없어서 선택값이에요. 없는 계정은 닉네임으로 로그인하고, 정보 수정에서 이메일을 추가할 수 있어요.
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # null for Google-only accounts
    google_sub: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    nickname: Mapped[str] = mapped_column(String(16))
    avatar_filename: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    tier: Mapped[Tier] = mapped_column(_enum(Tier))
    # 정보 수정에서 실력을 바꾸면 "다음 대결부터" 적용: next_tier becomes tier once next_tier_at passes.
    next_tier: Mapped[Optional[Tier]] = mapped_column(_enum(Tier), nullable=True)
    next_tier_at: Mapped[Optional[dt.datetime]] = mapped_column(UTCDateTime, nullable=True)

    points: Mapped[int] = mapped_column(Integer, default=0)  # spendable balance
    total_points: Mapped[int] = mapped_column(Integer, default=0)  # lifetime earned; drives level
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


# Nicknames are unique ignoring case ("Yuri" == "yuri").
Index("uq_users_nickname_lower", func.lower(User.nickname), unique=True)


class Photo(Base):
    """A photo taken with the in-app camera. captured_at is stamped by the server at upload."""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(64), unique=True)
    captured_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now, index=True)


class Battle(Base):
    """One battle. Two kinds run in parallel:

    - daily: one per (week, skill group), Monday 00:00 KST -> next Monday 00:00 KST.
    - theme: one shared battle for everyone (tier is null), running THEME_COOKING_DAYS.

    Both go cooking -> voting (a fixed VOTING_WINDOW after cook_ends_at) -> closed once
    finalized. `ends_at` is the *cooking* deadline; voting happens between ends_at and
    voting_ends_at, and finalize_due_battles() only runs once voting_ends_at has passed.
    """

    __tablename__ = "battles"
    __table_args__ = (
        # theme battles have tier=NULL, and SQLite treats NULLs as distinct in a UNIQUE
        # constraint, so daily and theme each get their own partial unique index instead.
        Index("uq_daily_battle_week_tier", "week_start", "tier", unique=True, sqlite_where=text("kind = 'daily'")),
        Index("uq_theme_battle_week", "week_start", unique=True, sqlite_where=text("kind = 'theme'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[BattleKind] = mapped_column(_enum(BattleKind), default=BattleKind.daily, index=True)
    tier: Mapped[Optional[Tier]] = mapped_column(_enum(Tier), nullable=True)  # null for kind=theme (everyone)
    theme: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(120))
    week_start: Mapped[dt.date] = mapped_column(Date)  # theme battles: the cooking-period start date
    starts_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    ends_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, index=True)  # cooking deadline
    voting_ends_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, index=True)
    # Set once, when ranks and rank points have been handed out (or the battle was voided).
    finalized_at: Mapped[Optional[dt.datetime]] = mapped_column(UTCDateTime, nullable=True)
    is_void: Mapped[bool] = mapped_column(Boolean, default=False)


class Entry(Base):
    """A user's submission to a battle (요리 인증). One per user per battle."""

    __tablename__ = "entries"
    __table_args__ = (UniqueConstraint("battle_id", "user_id", name="uq_one_entry_per_battle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(ForeignKey("battles.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id"), unique=True)  # a photo backs one entry only
    dish_name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(500), default="")
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    notify_on_close: Mapped[bool] = mapped_column(Boolean, default=False)  # "대회 종료 시 알림 받기"
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)

    # Filled in when the battle is finalized. rank stays null for void battles.
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rank_points: Mapped[int] = mapped_column(Integer, default=0)
    level_from: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    level_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship()
    battle: Mapped["Battle"] = relationship()
    photo: Mapped["Photo"] = relationship()


class Vote(Base):
    """Primary key (battle_id, voter_id) is what enforces 1인 1표 per battle."""

    __tablename__ = "votes"

    battle_id: Mapped[int] = mapped_column(ForeignKey("battles.id"), primary_key=True)
    voter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entries.id"), unique=True, nullable=True)

    title: Mapped[str] = mapped_column(String(60))
    category: Mapped[Category] = mapped_column(_enum(Category), index=True)
    cost_krw: Mapped[int] = mapped_column(Integer, index=True)
    cook_minutes: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[Tier] = mapped_column(_enum(Tier))
    win_label: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)  # "밥 요리 대결 1등"
    photo_filename: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # "자취 필수" 칩

    save_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now, index=True)

    author: Mapped["User"] = relationship()
    ingredients: Mapped[List["Ingredient"]] = relationship(
        cascade="all, delete-orphan", order_by="Ingredient.position"
    )
    steps: Mapped[List["Step"]] = relationship(cascade="all, delete-orphan", order_by="Step.position")
    tools: Mapped[List["RecipeTool"]] = relationship(cascade="all, delete-orphan")


class RecipeTool(Base):
    __tablename__ = "recipe_tools"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), primary_key=True)
    tool: Mapped[Tool] = mapped_column(_enum(Tool), primary_key=True)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # 1-based
    text: Mapped[str] = mapped_column(String(500))


class RecipeSave(Base):
    __tablename__ = "recipe_saves"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), primary_key=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class RecipeView(Base):
    """Last time each user opened each recipe (메뉴 > 최근 본 레시피)."""

    __tablename__ = "recipe_views"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), primary_key=True)
    viewed_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now, index=True)


class Review(Base):
    """A comment on a recipe. The design calls these 댓글 on the recipe and 후기 on the home screen."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)

    author: Mapped["User"] = relationship()
    recipe: Mapped["Recipe"] = relationship()


class ShopItem(Base):
    __tablename__ = "shop_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    price_points: Mapped[int] = mapped_column(Integer)
    required_level: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Exchange(Base):
    """A gifticon exchange. MVP: nothing is actually sent, this is the saved 교환 내역."""

    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    shop_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shop_items.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(60))
    points_spent: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class LedgerEntry(Base):
    """Append-only audit trail for every point change (points can become real gifticons)."""

    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    points_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    ref_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)
