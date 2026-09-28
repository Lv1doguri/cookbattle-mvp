import datetime as dt

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import clock
from ..content import MAX_UPLOADS_PER_HOUR, PHOTO_TTL
from ..database import get_db
from ..errors import ApiError
from ..models import Entry, Photo, User
from ..schemas import PhotoOut
from ..security import get_current_user
from ..services.accounts import count
from ..services.images import compute_phash, delete_image, find_duplicate, image_url, read_image, write_image

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("", response_model=PhotoOut, status_code=201)
def upload_camera_photo(
    file: UploadFile = File(..., description="앱 카메라로 방금 찍은 사진"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """촬영 직후 올리세요(multipart, 필드명 `file`). 서버가 촬영 시각을 찍고, `expires_at`까지
    대결 [제출]에 써야 해요. 한 번 제출한 사진은 다시 쓸 수 없어요."""
    now = clock.utcnow()
    if count(db, Photo, Photo.user_id == user.id, Photo.captured_at >= now - dt.timedelta(hours=1)) >= MAX_UPLOADS_PER_HOUR:
        raise ApiError(429, "too_many_uploads", "잠시 후 다시 시도해주세요")

    data, ext = read_image(file)  # validates before anything is written

    phash = compute_phash(data)
    existing = db.scalars(select(Photo.phash).where(Photo.phash.is_not(None))).all()
    if find_duplicate(phash, existing):
        raise ApiError(409, "photo_reused", "이전에 올린 적 있는 사진과 같은 사진이에요. 새로 찍어주세요")

    # Retakes and abandoned shots leave unused photos behind; sweep this user's expired ones.
    stale = db.scalars(
        select(Photo).where(
            Photo.user_id == user.id,
            Photo.captured_at < now - PHOTO_TTL,
            Photo.id.not_in(select(Entry.photo_id)),
            Photo.id.not_in(select(Entry.angle_photo_id).where(Entry.angle_photo_id.is_not(None))),
        )
    ).all()
    for old in stale:
        delete_image(old.filename)
    if stale:
        db.execute(delete(Photo).where(Photo.id.in_([p.id for p in stale])))

    photo = Photo(user_id=user.id, filename=write_image(data, ext), captured_at=now, phash=phash)
    db.add(photo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_image(photo.filename)
        raise
    return PhotoOut(
        photo_id=photo.id,
        photo_url=image_url(photo.filename),
        captured_at=photo.captured_at,
        expires_at=photo.captured_at + PHOTO_TTL,
    )
