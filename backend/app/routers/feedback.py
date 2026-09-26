"""대결 작품 평가(댓글 + 별점)와 신고."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Comment, Report, Submission, User
from ..schemas import (
    BattleCommentCreate, BattleCommentList, BattleCommentOut, BattleCommentUpdate, ReportCreate,
)
from ..services.serializers import battle_comment_out, rating_summary
from ..timeutil import utcnow

router = APIRouter(tags=["feedback"])


def _visible(db: Session, submission_id: int, user: User) -> Submission:
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if s is None or (s.is_hidden and s.user_id != user.id):
        raise HTTPException(status_code=404, detail="작품을 찾을 수 없습니다")
    return s


def _get_comment(db: Session, comment_id: int) -> Comment:
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if c is None:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")
    return c


@router.get("/submissions/{submission_id}/comments", response_model=BattleCommentList)
def list_comments(
    submission_id: int,
    sort: str = "latest",  # latest | rating_high | rating_low
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """작품의 평가 목록 + 별점 요약(평균, 개수, 분포)."""
    _visible(db, submission_id, user)
    rows = (
        db.query(Comment)
        .filter(Comment.submission_id == submission_id)
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .all()
    )
    if sort == "rating_high":
        rows.sort(key=lambda c: -(c.rating or 0))
    elif sort == "rating_low":
        rows.sort(key=lambda c: c.rating or 6)
    return BattleCommentList(
        summary=rating_summary(db, submission_id),
        comments=[battle_comment_out(c, user) for c in rows],
    )


@router.get("/submissions/{submission_id}/comments/mine", response_model=Optional[BattleCommentOut])
def my_comment(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """내가 이 작품에 남긴 평가 (없으면 null) — 작성/수정 화면 전환용."""
    _visible(db, submission_id, user)
    c = db.query(Comment).filter(Comment.submission_id == submission_id, Comment.user_id == user.id).first()
    return battle_comment_out(c, user) if c else None


@router.post("/submissions/{submission_id}/comments", response_model=BattleCommentOut)
def add_comment(submission_id: int, payload: BattleCommentCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """평가 작성 (댓글 + 별점 1~5). 한 작품에 1번, 내 작품에는 불가."""
    s = _visible(db, submission_id, user)
    if s.user_id == user.id:
        raise HTTPException(status_code=400, detail="내 작품에는 평가를 남길 수 없어요")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="평가 내용을 입력해 주세요")
    if db.query(Comment).filter(Comment.submission_id == submission_id, Comment.user_id == user.id).first():
        raise HTTPException(status_code=400, detail="이미 평가를 남겼어요. 기존 평가를 수정해 주세요")

    c = Comment(submission_id=submission_id, user_id=user.id, content=content, rating=payload.rating)
    db.add(c)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 평가를 남겼어요. 기존 평가를 수정해 주세요")
    db.refresh(c)
    return battle_comment_out(c, user)


@router.patch("/comments/{comment_id}", response_model=BattleCommentOut)
def update_comment(comment_id: int, payload: BattleCommentUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """내 평가 수정 (내용, 별점 중 바꿀 것만)."""
    c = _get_comment(db, comment_id)
    if c.user_id != user.id:
        raise HTTPException(status_code=403, detail="내 평가만 수정할 수 있어요")
    if payload.content is not None:
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="평가 내용을 입력해 주세요")
        c.content = content
    if payload.rating is not None:
        c.rating = payload.rating
    c.updated_at = utcnow()
    db.commit()
    db.refresh(c)
    return battle_comment_out(c, user)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _get_comment(db, comment_id)
    if c.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="내 평가만 삭제할 수 있어요")
    db.delete(c)
    db.commit()
    return {"deleted": True}


@router.post("/submissions/{submission_id}/report")
def report(submission_id: int, payload: ReportCreate, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    """인증샷 신고. REPORT_HIDE_THRESHOLD회 누적 시 자동 숨김 (진행 중 대결만)."""
    s = _visible(db, submission_id, user)
    if s.user_id == user.id:
        raise HTTPException(status_code=400, detail="내 작품은 신고할 수 없어요")
    db.add(Report(submission_id=submission_id, reporter_id=user.id, reason=payload.reason.strip()))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 신고한 작품입니다")
    count = db.query(Report).filter(Report.submission_id == submission_id).count()
    if count >= rules.REPORT_HIDE_THRESHOLD and not s.battle.is_closed:
        s.is_hidden = True
    db.commit()
    return {"submission_id": submission_id, "report_count": count, "is_hidden": s.is_hidden}
