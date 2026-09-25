import datetime as dt

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import clock
from ..content import BATTLE_REWARDS, WEEKLY_THEMES
from ..enums import Tier
from ..models import Battle


def get_or_create_battle(db: Session, tier: Tier, day: dt.date) -> Battle:
    """Battles are created lazily the first time anyone asks for (day, tier).

    Commits on creation, so only call it where there is no other pending work in the session.
    """
    stmt = select(Battle).where(Battle.date == day, Battle.tier == tier)
    battle = db.scalar(stmt)
    if battle is not None:
        return battle

    schedule = WEEKLY_THEMES[day.weekday()]
    xp, coins = BATTLE_REWARDS[tier]
    starts_at, ends_at = clock.kst_day_bounds(day)
    db.add(
        Battle(
            date=day,
            tier=tier,
            theme=schedule["theme"],
            description=schedule[tier],
            reward_xp=xp,
            reward_coins=coins,
            starts_at=starts_at,
            ends_at=ends_at,
        )
    )
    try:
        db.commit()
    except IntegrityError:  # another request created it first
        db.rollback()
    return db.scalar(stmt)
