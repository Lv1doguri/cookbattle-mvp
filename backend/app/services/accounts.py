import datetime as dt
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import clock
from ..enums import TIER_LABEL
from ..models import RecipeSave, Review, User
from ..schemas import MeOut, UserBrief
from .images import image_url
from .points import expire_points, progress_for


def count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def user_brief(u: User) -> UserBrief:
    return UserBrief(id=u.id, nickname=u.nickname, avatar_url=image_url(u.avatar_filename))


def nickname_taken(db: Session, nickname: str, exclude_user_id: Optional[int] = None) -> bool:
    stmt = select(User.id).where(func.lower(User.nickname) == nickname.strip().lower())
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


def current_week_end(now: dt.datetime) -> dt.datetime:
    monday = clock.kst_week_start(clock.kst_date(now))
    return clock.kst_day_bounds(monday + dt.timedelta(days=7))[0]


def build_me(db: Session, user: User) -> MeOut:
    expire_points(db, user, clock.utcnow())
    return MeOut(
        **user_brief(user).model_dump(),
        email=user.email,
        tier=user.tier,
        tier_label=TIER_LABEL[user.tier],
        pending_tier=user.next_tier,
        pending_tier_label=TIER_LABEL[user.next_tier] if user.next_tier else None,
        pending_tier_applies_at=user.next_tier_at,
        progress=progress_for(user),
        saved_recipe_count=count(db, RecipeSave, RecipeSave.user_id == user.id),
        review_count=count(db, Review, Review.author_id == user.id),
    )
