from typing import Optional

from sqlalchemy import case, update
from sqlalchemy.orm import Session

from ..content import XP_PER_LEVEL
from ..enums import TIER_LABEL
from ..models import LedgerEntry, User
from ..schemas import Progress


def level_for(xp: int) -> int:
    return xp // XP_PER_LEVEL + 1


def progress_for(user: User) -> Progress:
    level = level_for(user.xp)
    return Progress(
        tier=user.tier,
        tier_label=TIER_LABEL[user.tier] if user.tier else None,
        level=level,
        xp=user.xp,
        level_start_xp=(level - 1) * XP_PER_LEVEL,
        next_level_xp=level * XP_PER_LEVEL,
        xp_to_next_level=level * XP_PER_LEVEL - user.xp,
    )


def grant(
    db: Session,
    user: User,
    *,
    xp: int = 0,
    coins: int = 0,
    reason: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
) -> None:
    """Add XP/coins atomically in SQL and write a ledger row. Caller commits.

    XP is clamped at 0 (taking back a like's XP can never push a user negative).
    Coins are only ever added here; spending goes through spend_coins so it can be guarded.
    """
    if coins < 0:
        raise ValueError("use spend_coins() to subtract coins")
    db.execute(
        update(User)
        .where(User.id == user.id)
        .values(xp=case((User.xp + xp < 0, 0), else_=User.xp + xp), coins=User.coins + coins)
    )
    db.add(LedgerEntry(user_id=user.id, xp_delta=xp, coin_delta=coins, reason=reason, ref_type=ref_type, ref_id=ref_id))
    db.flush()
    db.refresh(user)


def spend_coins(
    db: Session,
    user: User,
    amount: int,
    *,
    reason: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
) -> bool:
    """Subtract coins only if the balance covers it, in a single UPDATE (no read-then-write race).

    Returns False (and changes nothing) when the balance is too low. Caller commits.
    """
    result = db.execute(
        update(User).where(User.id == user.id, User.coins >= amount).values(coins=User.coins - amount)
    )
    if result.rowcount != 1:
        return False
    db.add(LedgerEntry(user_id=user.id, coin_delta=-amount, reason=reason, ref_type=ref_type, ref_id=ref_id))
    db.flush()
    db.refresh(user)
    return True
