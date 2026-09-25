import contextlib
import datetime as dt
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from .. import clock
from ..config import settings
from ..content import MAX_UPLOADS_PER_HOUR, PHOTO_TTL
from ..database import get_db
from ..errors import ApiError
from ..models import Photo, User
from ..schemas import PhotoOut
from ..security import get_current_user
from ..services.serialize import count, photo_url

router = APIRouter(prefix="/photos", tags=["photos"])


def _image_extension(head: bytes) -> Optional[str]:
    """Decide the type from the file's own bytes; the client's filename/content-type are ignored."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


@router.post("", response_model=PhotoOut, status_code=201)
def upload_photo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """COOKUP 카메라로 찍은 사진을 올립니다. 촬영 시각은 서버가 찍고, 게시물에 붙일 수 있는 시간은 제한돼요."""
    now = clock.utcnow()
    recent = count(db, Photo, Photo.user_id == user.id, Photo.captured_at >= now - dt.timedelta(hours=1))
    if recent >= MAX_UPLOADS_PER_HOUR:
        raise ApiError(429, "too_many_uploads", "잠시 후 다시 시도해주세요")

    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise ApiError(413, "file_too_large", f"사진은 {settings.max_upload_bytes // (1024 * 1024)}MB 이하여야 해요")
    ext = _image_extension(data[:12])
    if ext is None:
        raise ApiError(400, "unsupported_image", "JPG, PNG, WEBP 사진만 올릴 수 있어요")

    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(settings.upload_dir, filename)
    with open(path, "wb") as f:
        f.write(data)

    photo = Photo(user_id=user.id, filename=filename, captured_at=now)
    db.add(photo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        with contextlib.suppress(OSError):
            os.remove(path)
        raise

    return PhotoOut(
        photo_id=photo.id,
        photo_url=photo_url(filename),
        captured_at=photo.captured_at,
        expires_at=photo.captured_at + PHOTO_TTL,
    )
