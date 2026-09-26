"""친구 관계 조회 도우미."""
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Friendship, User
from ..timeutil import utcnow


def find_pair(db: Session, a: int, b: int) -> Optional[Friendship]:
    """두 사람 사이의 관계 행 (방향 무관)."""
    return (
        db.query(Friendship)
        .filter(or_(
            (Friendship.requester_id == a) & (Friendship.addressee_id == b),
            (Friendship.requester_id == b) & (Friendship.addressee_id == a),
        ))
        .first()
    )


def relation(db: Session, me: User, other_id: int) -> tuple:
    """(관계, 요청 id). 관계: self | friend | request_sent | request_received | none"""
    if other_id == me.id:
        return "self", None
    f = find_pair(db, me.id, other_id)
    if f is None:
        return "none", None
    if f.status == "accepted":
        return "friend", f.id
    return ("request_sent" if f.requester_id == me.id else "request_received"), f.id


def friend_rows(db: Session, user_id: int) -> list:
    return (
        db.query(Friendship)
        .filter(Friendship.status == "accepted",
                or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id))
        .all()
    )


def friend_ids(db: Session, user_id: int) -> list:
    return [f.addressee_id if f.requester_id == user_id else f.requester_id for f in friend_rows(db, user_id)]


def make_friends(db: Session, a: User, b: User) -> None:
    """바로 친구로 연결 (초대 코드 가입 등). 이미 관계가 있으면 수락 상태로. commit은 호출하는 쪽에서."""
    f = find_pair(db, a.id, b.id)
    if f is None:
        db.add(Friendship(requester_id=a.id, addressee_id=b.id, status="accepted", responded_at=utcnow()))
    elif f.status != "accepted":
        f.status = "accepted"
        f.responded_at = utcnow()
    db.flush()
