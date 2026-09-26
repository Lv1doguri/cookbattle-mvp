import datetime as dt

from sqlalchemy.orm import Session

from .. import rules
from ..models import PointLog, User
from ..timeutil import utcnow


def award(db: Session, user: User, points: int, reason: str, ref: str, memo: str = "") -> bool:
    """포인트 적립 (누적 + 보유 둘 다 증가). 같은 (user, reason, ref)는 한 번만.
    DB에서 '현재값 + n'으로 더해서 동시에 적립돼도 값이 덮어써지지 않는다. commit은 호출하는 쪽에서."""
    if points <= 0:
        return False
    exists = (
        db.query(PointLog.id)
        .filter(PointLog.user_id == user.id, PointLog.reason == reason, PointLog.ref == ref)
        .first()
    )
    if exists:
        return False
    db.add(PointLog(user_id=user.id, points=points, reason=reason, ref=ref, memo=memo))
    user.total_points = User.total_points + points
    user.points = User.points + points
    db.flush()  # 이후 user.total_points를 읽으면 DB에서 새 값을 다시 읽어 온다
    return True


def expire_points(db: Session, user: User) -> int:
    """POINT_EXPIRY_DAYS가 지난 적립분을 보유(상점용) 포인트에서 소멸시킨다.
    누적 포인트(total_points, 레벨 계산용)는 줄지 않는다. commit은 호출하는 쪽에서."""
    cutoff = utcnow() - dt.timedelta(days=rules.POINT_EXPIRY_DAYS)
    logs = (
        db.query(PointLog)
        .filter(
            PointLog.user_id == user.id, PointLog.created_at < cutoff,
            PointLog.expired.is_(False), PointLog.points > 0,
        )
        .all()
    )
    if not logs:
        return 0
    total = sum(l.points for l in logs)
    for l in logs:
        l.expired = True
    deduct = min(total, user.points or 0)  # 이미 상점에서 써버린 만큼은 다시 깎지 않음
    if deduct > 0:
        user.points = User.points - deduct
        db.add(PointLog(user_id=user.id, points=-deduct, reason="expire", ref=f"expire:{utcnow():%Y%m%d}",
                        memo=f"{rules.POINT_EXPIRY_DAYS}일 경과로 포인트 소멸"))
    db.flush()
    return deduct
