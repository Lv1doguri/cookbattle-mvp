import datetime as dt
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Submission, Topic, User, Vote
from ..schemas import SubmissionOut

router = APIRouter(tags=["submissions"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8MB, generous enough for a phone photo


def _to_submission_out(sub: Submission, db: Session, user: User) -> SubmissionOut:
    vote_count = db.query(Vote).filter(Vote.submission_id == sub.id).count()
    has_voted = (
        db.query(Vote).filter(Vote.submission_id == sub.id, Vote.voter_id == user.id).first()
        is not None
    )
    return SubmissionOut(
        id=sub.id,
        topic_id=sub.topic_id,
        user_id=sub.user_id,
        nickname=sub.user.nickname,
        image_url=f"/uploads/{os.path.basename(sub.image_path)}",
        created_at=sub.created_at,
        vote_count=vote_count,
        is_mine=sub.user_id == user.id,
        has_voted=has_voted,
    )


@router.post("/topics/{topic_id}/submissions", response_model=SubmissionOut)
def create_submission(
    topic_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다")
    if topic.is_closed:
        raise HTTPException(status_code=400, detail="마감된 주제입니다")
    if topic.active_date != dt.date.today():
        raise HTTPException(status_code=400, detail="오늘의 주제가 아닙니다")

    existing = (
        db.query(Submission)
        .filter(Submission.topic_id == topic_id, Submission.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="이미 오늘 이 주제에 제출했습니다")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="지원하지 않는 이미지 형식입니다")

    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="파일 용량이 너무 큽니다 (최대 8MB)")

    os.makedirs(settings.upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    submission = Submission(topic_id=topic_id, user_id=user.id, image_path=filepath)
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return _to_submission_out(submission, db, user)


@router.get("/topics/{topic_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(topic_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다")

    subs = db.query(Submission).filter(Submission.topic_id == topic_id).all()
    return [_to_submission_out(s, db, user) for s in subs]
