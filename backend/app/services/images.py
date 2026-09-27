import contextlib
import io
import os
import uuid
from typing import Optional, Sequence, Tuple

from fastapi import UploadFile
from PIL import Image

from ..config import settings
from ..content import PHOTO_DUP_HAMMING_DISTANCE
from ..errors import ApiError


def image_url(filename: Optional[str]) -> Optional[str]:
    return f"/uploads/{filename}" if filename else None


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


def compute_phash(data: bytes) -> Optional[str]:
    """64-bit dHash, as a 16-char hex string. None if the bytes can't be decoded as an image
    (upload is still accepted; it just won't be checked for reuse)."""
    try:
        img = Image.open(io.BytesIO(data)).convert("L").resize((9, 8))
    except Exception:
        return None
    px = list(img.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (1 if px[row * 9 + col] > px[row * 9 + col + 1] else 0)
    return f"{bits:016x}"


def _hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def find_duplicate(phash: Optional[str], existing: Sequence[Optional[str]]) -> bool:
    """True if `phash` is within PHOTO_DUP_HAMMING_DISTANCE of any hash in `existing`."""
    if phash is None:
        return False
    return any(h is not None and _hamming(phash, h) <= PHOTO_DUP_HAMMING_DISTANCE for h in existing)
