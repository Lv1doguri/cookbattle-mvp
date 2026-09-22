from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Submission, User, Vote

router = APIRouter(tags=["votes"])


@router.post("/submissions/{submission_id}/vote")
def cast_vote(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if submission is None:
        raise HTTPException(status_code=404, detail="제출물을 찾을 수 없습니다")

    if submission.user_id == user.id:
        raise HTTPException(status_code=400, detail="본인 제출물에는 투표할 수 없습니다")

    # one vote per voter per topic (not just per submission) — check any existing vote by this
    # user on any submission belonging to the same topic
    already_voted = (
        db.query(Vote)
        .join(Submission, Vote.submission_id == Submission.id)
        .filter(Submission.topic_id == submission.topic_id, Vote.voter_id == user.id)
        .first()
    )
    if already_voted:
        raise HTTPException(status_code=400, detail="이 주제에는 이미 투표하셨습니다")

    vote = Vote(submission_id=submission_id, voter_id=user.id)
    db.add(vote)
    db.commit()

    vote_count = db.query(Vote).filter(Vote.submission_id == submission_id).count()
    return {"submission_id": submission_id, "vote_count": vote_count}
