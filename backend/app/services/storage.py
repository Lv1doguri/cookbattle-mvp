"""이미지 저장. 모든 사진은 검사(photo_check) 후 EXIF를 지운 JPEG로 저장된다."""
import os
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile

from .. import rules
from ..config import settings
from .photo_check import PhotoError, PhotoInfo, analyze, to_jpeg_bytes

CHUNK = 1024 * 1024


def read_limited(upload: UploadFile) -> bytes:
    buf = bytearray()
    while True:
        chunk = upload.file.read(CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > rules.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="파일 용량이 너무 커요 (장당 최대 8MB)")
    return bytes(buf)


def inspect_upload(upload: UploadFile, label: str = "") -> PhotoInfo:
    """업로드 파일을 읽어 검사. 실패하면 400 (label이 있으면 '‘구도’ 사진: ...' 형태)."""
    try:
        return analyze(read_limited(upload))
    except PhotoError as e:
        raise HTTPException(status_code=400, detail=f"'{label}' 사진: {e}" if label else str(e))


def save_photo(info: PhotoInfo) -> str:
    os.makedirs(settings.upload_dir, exist_ok=True)
    path = os.path.join(settings.upload_dir, f"{uuid.uuid4().hex}.jpg")
    with open(path, "wb") as f:
        f.write(to_jpeg_bytes(info.image))
    return path


def save_image(upload: UploadFile) -> str:
    """단일 사진(레시피 사진, 따라하기 인증 등) 검사 후 저장."""
    return save_photo(inspect_upload(upload))


def delete_files(paths: list) -> None:
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass


def to_url(path: Optional[str]) -> str:
    if not path:
        return ""
    return f"/uploads/{os.path.basename(path)}"
