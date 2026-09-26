from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Submission, User, Vote
from ..schemas import VoteResponse
from ..services.battle import close_expired_battles, vote_block_reason, vote_counts
from ..services.points import award
from ..services.serializers import show_votes

router = APIRouter(tags=["votes"])


@router.post("/submissions/{submission_id}/vote", response_model=VoteResponse)
def vote(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """1인 1표 (대결당). 본문 없음. 투표 기간에만, 그 대결에 참가한 사람만 가능. 투표하면 +VOTE_POINTS."""
    close_expired_battles(db)
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if s is None or s.is_hidden:
        raise HTTPException(status_code=404, detail="작품을 찾을 수 없습니다")
    if s.user_id == user.id:
        raise HTTPException(status_code=400, detail="내 작품에는 투표할 수 없어요")
    reason = vote_block_reason(db, s.battle, user)
    if reason:
        status = 403 if "참가한 사람만" in reason or "숨김" in reason else 400
        raise HTTPException(status_code=status, detail=reason)

    db.add(Vote(battle_id=s.battle_id, submission_id=s.id, voter_id=user.id))
    try:
        db.flush()
        award(db, user, rules.VOTE_POINTS, "vote", f"battle:{s.battle_id}", memo="투표 참여")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 투표하셨습니다")
    count = vote_counts(db, s.battle_id).get(s.id, 0)
    return VoteResponse(submission_id=s.id, vote_count=count if show_votes(s.battle) else None)
