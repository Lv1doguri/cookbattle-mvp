import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Submission, Topic, User, Vote
from ..schemas import ResultEntry, TopicResults

router = APIRouter(tags=["results"])


@router.get("/topics/{topic_id}/results", response_model=TopicResults)
def get_results(topic_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다")

    rows = (
        db.query(Submission, func.count(Vote.id).label("vote_count"))
        .outerjoin(Vote, Vote.submission_id == Submission.id)
        .filter(Submission.topic_id == topic_id)
        .group_by(Submission.id)
        # tie-break: higher votes first, then earlier submission time wins
        .order_by(func.count(Vote.id).desc(), Submission.created_at.asc())
        .all()
    )

    entries: list[ResultEntry] = []
    for idx, (sub, vote_count) in enumerate(rows):
        entries.append(
            ResultEntry(
                submission_id=sub.id,
                nickname=sub.user.nickname,
                image_url=f"/uploads/{os.path.basename(sub.image_path)}",
                vote_count=vote_count,
                rank=idx + 1,
                is_winner=(idx == 0 and vote_count > 0),
            )
        )

    return TopicResults(
        topic_id=topic.id,
        topic_name=topic.name,
        is_closed=topic.is_closed,
        entries=entries,
    )
