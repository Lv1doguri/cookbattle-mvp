import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Submission, Topic, User
from ..schemas import TopicOut

router = APIRouter(prefix="/topics", tags=["topics"])


def _to_topic_out(topic: Topic, db: Session, user: Optional[User]) -> TopicOut:
    submission_count = db.query(Submission).filter(Submission.topic_id == topic.id).count()
    has_submitted = False
    if user is not None:
        has_submitted = (
            db.query(Submission)
            .filter(Submission.topic_id == topic.id, Submission.user_id == user.id)
            .first()
            is not None
        )
    out = TopicOut.model_validate(topic)
    out.submission_count = submission_count
    out.has_submitted = has_submitted
    return out


@router.get("/today", response_model=list[TopicOut])
def list_today_topics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = dt.date.today()
    topics = db.query(Topic).filter(Topic.active_date == today).all()
    return [_to_topic_out(t, db, user) for t in topics]


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다")
    return _to_topic_out(topic, db, user)
