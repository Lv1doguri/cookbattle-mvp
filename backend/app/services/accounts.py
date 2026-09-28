import datetime as dt
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import clock
from ..enums import TIER_LABEL
from ..models import RecipeSave, Review, User
from ..schemas import MeOut, UserBrief
from .images import image_url
from .points import progress_for


def count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def user_brief(u: User) -> UserBrief:
    return UserBrief(id=u.id, nickname=u.nickname, avatar_url=image_url(u.avatar_filename))


def nickname_taken(db: Session, nickname: str, exclude_user_id: Optional[int] = None) -> bool:
    stmt = select(User.id).where(func.lower(User.nickname) == nickname.strip().lower())
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return db.scalar(stmt) is not None


def username_taken(db: Session, username: str, exclude_user_id: Optional[int] = None) -> bool:
    stmt = select(User.id).where(func.lower(User.username) == username.strip().lower())
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return db.scalar(stmt) is not None


def apply_pending_tier(db: Session, user: User, now: dt.datetime) -> None:
    """정보 수정에서 바꾼 실력은 다음 대결부터 적용: once the scheduled time passes, switch over."""
    if user.next_tier is not None and user.next_tier_at is not None and now >= user.next_tier_at:
        user.tier = user.next_tier
        user.next_tier = None
        user.next_tier_at = None
        db.commit()


def next_daily_battle_start(now: dt.datetime) -> dt.datetime:
    """내일 00:00 KST — 실력 그룹을 바꾸면 "다음 대결부터" 적용되는데, 대결이 매일 열리니 그게 곧 내일이에요."""
    today = clock.kst_date(now)
    return clock.kst_day_bounds(today + dt.timedelta(days=1))[0]


def build_me(db: Session, user: User) -> MeOut:
    return MeOut(
        **user_brief(user).model_dump(),
        username=user.username,
        email=user.email,
        tier=user.tier,
        tier_label=TIER_LABEL[user.tier],
        pending_tier=user.next_tier,
        pending_tier_label=TIER_LABEL[user.next_tier] if user.next_tier else None,
        pending_tier_applies_at=user.next_tier_at,
        progress=progress_for(user),
        saved_recipe_count=count(db, RecipeSave, RecipeSave.user_id == user.id),
        review_count=count(db, Review, Review.author_id == user.id),
        streak_weeks=user.streak_weeks,
    )
