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
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from . import clock
from .database import Base
from .enums import Category, ShopCategory, Tier


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
        CheckConstraint("coins >= 0", name="ck_users_coins_nonneg"),
        CheckConstraint("xp >= 0", name="ck_users_xp_nonneg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str] = mapped_column(String(30))
    handle: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    bio: Mapped[str] = mapped_column(String(200), default="")
    tier: Mapped[Optional[Tier]] = mapped_column(_enum(Tier), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (CheckConstraint("follower_id != followee_id", name="ck_follow_not_self"),)

    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    followee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class Photo(Base):
    """A photo taken with the in-app camera. captured_at is stamped by the server."""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(64), unique=True)
    captured_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now, index=True)


class Battle(Base):
    """One battle per (KST day, tier)."""

    __tablename__ = "battles"
    __table_args__ = (UniqueConstraint("date", "tier", name="uq_battle_date_tier"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date)
    tier: Mapped[Tier] = mapped_column(_enum(Tier))
    theme: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(120))
    reward_xp: Mapped[int] = mapped_column(Integer)
    reward_coins: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    ends_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, index=True)


class Post(Base):
    """A cooking post. Every post carries its recipe (title/ingredients/steps/cost/time/difficulty)."""

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("battle_id", "author_id", name="uq_one_entry_per_battle"),
        Index("ix_posts_battle_score", "battle_id", "battle_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id"), unique=True)
    battle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("battles.id"), nullable=True)

    caption: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(60))
    category: Mapped[Optional[Category]] = mapped_column(_enum(Category), nullable=True)
    cost_krw: Mapped[int] = mapped_column(Integer, index=True)
    cook_minutes: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[Tier] = mapped_column(_enum(Tier))

    battle_score: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0)
    reward_coins: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now, index=True)

    author: Mapped["User"] = relationship()
    photo: Mapped["Photo"] = relationship()
    ingredients: Mapped[List["Ingredient"]] = relationship(
        cascade="all, delete-orphan", order_by="Ingredient.position"
    )
    steps: Mapped[List["Step"]] = relationship(cascade="all, delete-orphan", order_by="Step.position")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # 1-based
    text: Mapped[str] = mapped_column(String(500))


class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True, index=True)
    # true if this like paid out XP to the author, so un-liking knows whether to take it back
    xp_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class Save(Base):
    __tablename__ = "saves"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("comments.id"), nullable=True)
    text: Mapped[str] = mapped_column(String(500))
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)

    author: Mapped["User"] = relationship()


class CommentLike(Base):
    __tablename__ = "comment_likes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id"), primary_key=True, index=True)


class RecipeRating(Base):
    __tablename__ = "recipe_ratings"
    __table_args__ = (CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_range"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True, index=True)
    score: Mapped[int] = mapped_column(Integer)


class ShopItem(Base):
    __tablename__ = "shop_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    category: Mapped[ShopCategory] = mapped_column(_enum(ShopCategory))
    value_label: Mapped[str] = mapped_column(String(30))
    value_krw: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_coins: Mapped[int] = mapped_column(Integer)
    validity_days: Mapped[int] = mapped_column(Integer, default=90)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Coupon(Base):
    """A purchased coupon. Name/value are snapshots so later shop edits don't rewrite history."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    shop_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shop_items.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(60))
    value_label: Mapped[str] = mapped_column(String(30))
    value_krw: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_paid: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)
    expires_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[Optional[dt.datetime]] = mapped_column(UTCDateTime, nullable=True)


class LedgerEntry(Base):
    """Append-only audit trail for every XP/coin change (coins can become real coupons)."""

    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    xp_delta: Mapped[int] = mapped_column(Integer, default=0)
    coin_delta: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(40))
    ref_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=_now)
