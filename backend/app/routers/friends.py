"""친구: 검색, 요청/수락/거절/취소, 목록, 삭제, 친구 랭킹, 친구 활동, 공개 프로필."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Battle, Friendship, Submission, User
from ..schemas import (
    FriendOut, FriendRequestCreate, FriendRequestOut, RankingEntry, UserBrief, UserSearchOut,
)
from ..services.battle import compute_rankings
from ..services.friends import find_pair, friend_ids, friend_rows, relation
from ..services.storage import to_url
from ..timeutil import to_local_str, utcnow

router = APIRouter(tags=["friends"])


def _brief(u: User) -> dict:
    return {"user_id": u.id, "nickname": u.nickname, "level": u.level, "skill": u.skill,
            "skill_label": rules.skill_label(u.skill)}


def _request_out(f: Friendship) -> FriendRequestOut:
    return FriendRequestOut(
        id=f.id, from_user=UserBrief(**_brief(f.requester)), to_user=UserBrief(**_brief(f.addressee)),
        created_at=f.created_at, created_at_display=to_local_str(f.created_at),
    )


def _get_user(db: Session, user_id: int) -> User:
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return u


def _win_count(db: Session, user_id: int) -> int:
    wins = 0
    closed = (
        db.query(Battle)
        .join(Submission, Submission.battle_id == Battle.id)
        .filter(Submission.user_id == user_id, Battle.is_closed.is_(True), Battle.is_void.is_(False))
        .all()
    )
    for b in closed:
        entries = compute_rankings(db, b)
        if entries and entries[0].submission.user_id == user_id and entries[0].votes > 0:
            wins += 1
    return wins


# ---------- 검색 / 프로필 ----------

@router.get("/users/search", response_model=list[UserSearchOut])
def search_users(nickname: str = Query(..., max_length=30), db: Session = Depends(get_db),
                 me: User = Depends(get_current_user)):
    """닉네임 검색 (부분 일치, 최대 20명). 각 사람과의 관계도 함께."""
    q = nickname.strip()
    if not q:
        return []
    users = (
        db.query(User)
        .filter(User.nickname.contains(q), User.id != me.id)
        .order_by(User.nickname)
        .limit(20)
        .all()
    )
    out = []
    for u in users:
        rel, rid = relation(db, me, u.id)
        out.append(UserSearchOut(**_brief(u), relation=rel, request_id=rid))
    return out


@router.get("/users/{user_id}/profile")
def public_profile(user_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    """다른 사용자의 공개 프로필: 레벨, 실력, 대결 참가·우승 수, 최근 작품, 나와의 관계."""
    u = _get_user(db, user_id)
    rel, rid = relation(db, me, u.id)
    subs = (
        db.query(Submission)
        .filter(Submission.user_id == u.id, Submission.is_hidden.is_(False))
        .order_by(Submission.created_at.desc())
        .all()
    )
    return {
        **_brief(u),
        "total_points": u.total_points or 0,
        "battle_count": len(subs),
        "win_count": _win_count(db, u.id),
        "friend_count": len(friend_ids(db, u.id)),
        "relation": rel,
        "request_id": rid,
        "recent_submissions": [
            {"submission_id": s.id, "battle_id": s.battle_id, "category_name": s.battle.category.name,
             "title": s.title, "image_url": to_url(s.images[0].path) if s.images else "",
             "created_at_display": to_local_str(s.created_at)}
            for s in subs[:6]
        ],
    }


# ---------- 친구 요청 ----------

@router.post("/friends/requests")
def send_request(payload: FriendRequestCreate, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    """친구 요청 (닉네임 또는 user_id). 상대가 이미 나에게 요청했다면 바로 친구가 된다."""
    if payload.user_id is not None:
        target = db.query(User).filter(User.id == payload.user_id).first()
    elif payload.nickname:
        target = db.query(User).filter(User.nickname == payload.nickname.strip()).first()
    else:
        raise HTTPException(status_code=400, detail="닉네임을 입력해 주세요")
    if target is None:
        raise HTTPException(status_code=404, detail="해당 닉네임의 사용자가 없어요")
    if target.id == me.id:
        raise HTTPException(status_code=400, detail="나 자신에게는 친구 요청을 보낼 수 없어요")

    existing = find_pair(db, me.id, target.id)
    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="이미 친구예요")
        if existing.requester_id == me.id:
            raise HTTPException(status_code=400, detail="이미 친구 요청을 보냈어요")
        # 상대가 먼저 보낸 요청이 있으면 → 수락 처리
        existing.status = "accepted"
        existing.responded_at = utcnow()
        db.commit()
        return {"status": "accepted", "request_id": existing.id, "friend": _brief(target),
                "message": f"{target.nickname}님과 친구가 되었어요"}

    if len(friend_ids(db, me.id)) >= rules.MAX_FRIENDS:
        raise HTTPException(status_code=400, detail=f"친구는 최대 {rules.MAX_FRIENDS}명까지예요")
    pending = db.query(Friendship).filter(Friendship.requester_id == me.id, Friendship.status == "pending").count()
    if pending >= rules.MAX_PENDING_FRIEND_REQUESTS:  # 요청 도배 방지
        raise HTTPException(status_code=400, detail="수락 대기 중인 요청이 너무 많아요. 보낸 요청을 정리해 주세요")
    f = Friendship(requester_id=me.id, addressee_id=target.id, status="pending")
    db.add(f)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 친구 요청을 보냈어요")
    db.refresh(f)
    return {"status": "pending", "request_id": f.id, "friend": _brief(target),
            "message": f"{target.nickname}님에게 친구 요청을 보냈어요"}


@router.get("/friends/requests", response_model=list[FriendRequestOut])
def list_requests(box: str = "received", db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    """받은 요청(box=received, 기본) 또는 보낸 요청(box=sent)."""
    q = db.query(Friendship).filter(Friendship.status == "pending")
    q = q.filter(Friendship.requester_id == me.id) if box == "sent" else q.filter(Friendship.addressee_id == me.id)
    return [_request_out(f) for f in q.order_by(Friendship.created_at.desc()).all()]


def _pending_for(db: Session, request_id: int) -> Friendship:
    f = db.query(Friendship).filter(Friendship.id == request_id, Friendship.status == "pending").first()
    if f is None:
        raise HTTPException(status_code=404, detail="친구 요청을 찾을 수 없어요")
    return f


@router.post("/friends/requests/{request_id}/accept")
def accept_request(request_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    f = _pending_for(db, request_id)
    if f.addressee_id != me.id:
        raise HTTPException(status_code=403, detail="내가 받은 요청만 수락할 수 있어요")
    if len(friend_ids(db, me.id)) >= rules.MAX_FRIENDS:
        raise HTTPException(status_code=400, detail=f"친구는 최대 {rules.MAX_FRIENDS}명까지예요")
    f.status = "accepted"
    f.responded_at = utcnow()
    db.commit()
    return {"status": "accepted", "friend": _brief(f.requester),
            "message": f"{f.requester.nickname}님과 친구가 되었어요"}


@router.post("/friends/requests/{request_id}/reject")
def reject_request(request_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    f = _pending_for(db, request_id)
    if f.addressee_id != me.id:
        raise HTTPException(status_code=403, detail="내가 받은 요청만 거절할 수 있어요")
    db.delete(f)
    db.commit()
    return {"status": "rejected"}


@router.delete("/friends/requests/{request_id}")
def cancel_request(request_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    f = _pending_for(db, request_id)
    if f.requester_id != me.id:
        raise HTTPException(status_code=403, detail="내가 보낸 요청만 취소할 수 있어요")
    db.delete(f)
    db.commit()
    return {"status": "canceled"}


# ---------- 친구 목록 / 삭제 ----------

@router.get("/friends", response_model=list[FriendOut])
def list_friends(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    out = []
    for f in friend_rows(db, me.id):
        u = f.addressee if f.requester_id == me.id else f.requester
        last = (
            db.query(Submission.created_at)
            .filter(Submission.user_id == u.id)
            .order_by(Submission.created_at.desc())
            .first()
        )
        out.append(FriendOut(
            **_brief(u), total_points=u.total_points or 0, friends_since=f.responded_at or f.created_at,
            last_cooked_at=to_local_str(last[0]) if last else None,
            battle_count=db.query(Submission).filter(Submission.user_id == u.id).count(),
        ))
    out.sort(key=lambda x: x.nickname)
    return out


@router.delete("/friends/{user_id}")
def remove_friend(user_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    f = find_pair(db, me.id, user_id)
    if f is None or f.status != "accepted":
        raise HTTPException(status_code=404, detail="친구가 아니에요")
    db.delete(f)
    db.commit()
    return {"status": "removed"}


# ---------- 친구 랭킹 / 활동 ----------

@router.get("/friends/ranking", response_model=list[RankingEntry])
def friends_ranking(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    """나 + 친구들의 누적 포인트 순위 (동점이면 레벨 → 닉네임 순)."""
    ids = friend_ids(db, me.id) + [me.id]
    users = db.query(User).filter(User.id.in_(ids)).all()
    users.sort(key=lambda u: (-(u.total_points or 0), u.nickname))
    return [
        RankingEntry(**_brief(u), rank=i + 1, total_points=u.total_points or 0,
                     win_count=_win_count(db, u.id), is_me=u.id == me.id)
        for i, u in enumerate(users)
    ]


@router.get("/friends/activity")
def friends_activity(limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db),
                     me: User = Depends(get_current_user)):
    """친구들의 최근 대결 참가 소식 (최신순). 탭하면 GET /submissions/{id}로 작품 보기."""
    ids = friend_ids(db, me.id)
    if not ids:
        return []
    subs = (
        db.query(Submission)
        .filter(Submission.user_id.in_(ids), Submission.is_hidden.is_(False))
        .order_by(Submission.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "submission_id": s.id, "battle_id": s.battle_id,
            "user": _brief(s.user),
            "category_name": s.battle.category.name,
            "title": s.title,
            "image_url": to_url(s.images[0].path) if s.images else "",
            "created_at_display": to_local_str(s.created_at),
            "message": f"{s.user.nickname}님이 '{s.battle.category.name}' 대결에 '{s.title}'(으)로 참가했어요",
        }
        for s in subs
    ]
