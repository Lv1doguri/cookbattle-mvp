"""배틀 작품 평가: 댓글 + 별점(1~5). 한 사람이 한 작품에 1개(수정 가능), 내 작품에는 불가."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import clock
from ..database import get_db
from ..errors import ApiError
from ..models import Entry, EntryComment, User
from ..schemas import EntryCommentCreateIn, EntryCommentOut, EntryCommentPage, EntryCommentUpdateIn, RatingSummaryOut
from ..security import get_current_user
from ..services.accounts import user_brief

router = APIRouter(tags=["entry_comments"])


def _get_entry(db: Session, entry_id: int) -> Entry:
    entry = db.get(Entry, entry_id)
    if entry is None:
        raise ApiError(404, "entry_not_found", "출품작을 찾을 수 없습니다")
    return entry


def _out(c: EntryComment, viewer_id: int) -> EntryCommentOut:
    return EntryCommentOut(
        id=c.id, entry_id=c.entry_id, author=user_brief(c.user), text=c.text, rating=c.rating,
        created_at=c.created_at, is_edited=c.updated_at is not None, is_mine=c.user_id == viewer_id,
    )


def _summary(rows) -> RatingSummaryOut:
    ratings = [r.rating for r in rows]
    dist = {str(n): ratings.count(n) for n in (5, 4, 3, 2, 1)}
    avg = round(sum(ratings) / len(ratings), 1) if ratings else None
    return RatingSummaryOut(average=avg, count=len(ratings), distribution=dist)


@router.post("/entries/{entry_id}/comments", response_model=EntryCommentOut, status_code=201)
def create_comment(
    entry_id: int, body: EntryCommentCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    entry = _get_entry(db, entry_id)
    if entry.user_id == user.id:
        raise ApiError(400, "own_entry", "내 작품에는 평가를 남길 수 없어요")
    existing = db.scalar(select(EntryComment).where(EntryComment.entry_id == entry_id, EntryComment.user_id == user.id))
    if existing is not None:
        raise ApiError(409, "already_reviewed", "이미 평가를 남겼어요. 기존 평가를 수정해주세요")
    comment = EntryComment(entry_id=entry_id, user_id=user.id, text=body.text, rating=body.rating, created_at=clock.utcnow())
    db.add(comment)
    db.commit()
    return _out(comment, user.id)


@router.get("/entries/{entry_id}/comments", response_model=EntryCommentPage)
def list_comments(
    entry_id: int,
    sort: Literal["latest", "rating_high", "rating_low"] = Query("latest"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_entry(db, entry_id)
    stmt = select(EntryComment).options(joinedload(EntryComment.user)).where(EntryComment.entry_id == entry_id)
    if sort == "rating_high":
        stmt = stmt.order_by(EntryComment.rating.desc(), EntryComment.created_at.desc())
    elif sort == "rating_low":
        stmt = stmt.order_by(EntryComment.rating.asc(), EntryComment.created_at.desc())
    else:
        stmt = stmt.order_by(EntryComment.created_at.desc(), EntryComment.id.desc())
    rows = db.scalars(stmt).all()
    return EntryCommentPage(summary=_summary(rows), items=[_out(c, user.id) for c in rows])


@router.get("/entries/{entry_id}/comments/mine", response_model=Optional[EntryCommentOut])
def my_comment(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_entry(db, entry_id)
    c = db.scalar(select(EntryComment).where(EntryComment.entry_id == entry_id, EntryComment.user_id == user.id))
    return _out(c, user.id) if c else None


@router.patch("/comments/{comment_id}", response_model=EntryCommentOut)
def update_comment(
    comment_id: int, body: EntryCommentUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    c = db.get(EntryComment, comment_id)
    if c is None:
        raise ApiError(404, "comment_not_found", "평가를 찾을 수 없습니다")
    if c.user_id != user.id:
        raise ApiError(403, "not_your_comment", "본인 평가만 수정할 수 있어요")
    if body.text is not None:
        c.text = body.text
    if body.rating is not None:
        c.rating = body.rating
    c.updated_at = clock.utcnow()
    db.commit()
    return _out(c, user.id)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(EntryComment, comment_id)
    if c is None:
        raise ApiError(404, "comment_not_found", "평가를 찾을 수 없습니다")
    if c.user_id != user.id and not user.is_admin:
        raise ApiError(403, "not_your_comment", "본인 평가만 삭제할 수 있어요")
    db.delete(c)
    db.commit()
    return {"deleted": True}
