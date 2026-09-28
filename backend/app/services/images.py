import contextlib
import os
import shutil
import uuid
from typing import Optional, Tuple

from fastapi import UploadFile

from ..config import settings
from ..errors import ApiError


def image_url(filename: Optional[str]) -> Optional[str]:
    return f"/uploads/{filename}" if filename else None


def duplicate_image(filename: str) -> str:
    """Makes an independent copy of an upload under a fresh name, so the new owner
    (e.g. a review) doesn't break if the original row's photo later gets cleaned up."""
    _, ext = os.path.splitext(filename)
    new_filename = f"{uuid.uuid4().hex}{ext}"
    shutil.copyfile(
        os.path.join(settings.upload_dir, filename),
        os.path.join(settings.upload_dir, new_filename),
    )
    return new_filename


def _extension(head: bytes) -> Optional[str]:
    """Decide the type from the file's own bytes; the client's filename/content-type are ignored."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def read_image(file: UploadFile) -> Tuple[bytes, str]:
    """Validate an upload and return (bytes, extension). Raises ApiError; writes nothing."""
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise ApiError(413, "file_too_large", f"사진은 {settings.max_upload_bytes // (1024 * 1024)}MB 이하여야 해요")
    ext = _extension(data[:12])
    if ext is None:
        raise ApiError(400, "unsupported_image", "JPG, PNG, WEBP 사진만 올릴 수 있어요")
    return data, ext


def write_image(data: bytes, ext: str) -> str:
    filename = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(settings.upload_dir, filename), "wb") as f:
        f.write(data)
    return filename


def delete_image(filename: Optional[str]) -> None:
    if filename:
        with contextlib.suppress(OSError):
            os.remove(os.path.join(settings.upload_dir, filename))
