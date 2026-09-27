import datetime as dt
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..content import POINTS_EXPIRE_AFTER, level_threshold
from ..models import LedgerEntry, User
from ..schemas import Progress


def level_for(total_points: int) -> int:
    level = 1
    while level_threshold(level + 1) <= total_points:
        level += 1
    return level


def progress_for(user: User) -> Progress:
    level = level_for(user.total_points)
    next_points = level_threshold(level + 1)
    return Progress(
        level=level,
        points=user.points,
        total_points=user.total_points,
        level_start_points=level_threshold(level),
        next_level_points=next_points,
        points_to_next_level=next_points - user.total_points,
    )


def grant_points(
    db: Session,
    user: User,
    amount: int,
    *,
    reason: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
) -> None:
    """Add points (balance and lifetime total) in one SQL UPDATE and write a ledger row. Caller commits."""
    if amount <= 0:
        raise ValueError("grant_points needs a positive amount")
    db.execute(
        update(User)
        .where(User.id == user.id)
        .values(points=User.points + amount, total_points=User.total_points + amount)
    )
    db.add(LedgerEntry(user_id=user.id, points_delta=amount, reason=reason, ref_type=ref_type, ref_id=ref_id))
    db.flush()
    db.refresh(user)


def spend_points(
    db: Session,
    user: User,
    amount: int,
    *,
    reason: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
) -> bool:
    """Subtract from the balance only if it covers `amount`, in a single UPDATE (no read-then-write race).

    Lifetime total_points is untouched, so spending never lowers the level.
    Returns False (and changes nothing) when the balance is too low. Caller commits.
    """
    result = db.execute(
        update(User).where(User.id == user.id, User.points >= amount).values(points=User.points - amount)
    )
    if result.rowcount != 1:
        return False
    db.add(LedgerEntry(user_id=user.id, points_delta=-amount, reason=reason, ref_type=ref_type, ref_id=ref_id))
    db.flush()
    db.refresh(user)
    return True


def expire_points(db: Session, user: User, now: dt.datetime) -> int:
    """Claw back spendable balance earned more than POINTS_EXPIRE_AFTER ago (lifetime total/level
    are untouched). Called lazily (on /me, /me/home, /shop) rather than by a scheduler. Idempotent:
    each positive ledger row is only ever counted once (`expired` flag)."""
    cutoff = now - POINTS_EXPIRE_AFTER
    rows = db.scalars(
        select(LedgerEntry).where(
            LedgerEntry.user_id == user.id,
            LedgerEntry.created_at < cutoff,
            LedgerEntry.expired.is_(False),
            LedgerEntry.points_delta > 0,
        )
    ).all()
    if not rows:
        return 0
    total = sum(r.points_delta for r in rows)
    for r in rows:
        r.expired = True
    deduct = min(total, user.points)  # never claw back points already spent
    if deduct > 0:
        db.execute(update(User).where(User.id == user.id).values(points=User.points - deduct))
        db.add(LedgerEntry(user_id=user.id, points_delta=-deduct, reason="expire", expired=True))
    db.commit()
    db.refresh(user)
    return deduct
