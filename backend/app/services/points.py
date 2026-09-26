from sqlalchemy.orm import Session

from ..models import PointLog, User


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
