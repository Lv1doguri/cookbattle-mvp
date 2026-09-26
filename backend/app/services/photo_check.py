"""인증샷 검사 알고리즘 (Pillow만 사용, 외부 AI 없음).

1) 형식 검사   : 실제 이미지(jpg/png/webp)인지 내용을 열어서 확인
2) 품질 검사   : 해상도(짧은 변), 밝기(너무 어두움), 대비(빈/단색 사진)
3) 지각 해시   : dHash(64비트)로 '같은 사진' 판별
                 - 한 번에 올린 사진끼리 → 같은 사진을 여러 구도인 척 올리는 것 차단
                 - 이전에 올라온 모든 사진과 → 예전 사진 재사용·남의 사진 도용 차단
4) 촬영 시각   : EXIF 촬영일이 있으면 대결 기간 안인지 확인 (없으면 '미인증'으로만 표시)
5) 저장        : 방향 보정 후 EXIF(위치정보 포함)를 모두 지우고 JPEG로 재저장 → 자취방 위치 노출 방지

한계: 실제로 '위에서' 찍었는지 같은 구도 자체는 판별하지 않는다(이미지 인식 모델 필요).
     구도는 촬영 가이드 + 같은 사진 차단 + 신고 기능으로 보완한다.
"""
import datetime as dt
import io
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from .. import rules

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 50_000_000
EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 36867
TAG_DATETIME = 306


class PhotoError(Exception):
    """사용자에게 그대로 보여줄 수 있는 한국어 메시지를 담는다."""


@dataclass
class PhotoInfo:
    image: Image.Image  # 방향 보정된 RGB 이미지
    dhash: str  # 16자리 hex (64비트)
    taken_at: Optional[dt.datetime]  # EXIF 촬영 시각 (카메라 현지 시간), 없으면 None


def _taken_at(img: Image.Image) -> Optional[dt.datetime]:
    try:
        exif = img.getexif()
        raw = exif.get_ifd(EXIF_IFD).get(TAG_DATETIME_ORIGINAL) or exif.get(TAG_DATETIME)
        if not raw:
            return None
        return dt.datetime.strptime(str(raw).strip("\x00 ").strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def dhash(img: Image.Image, size: int = 8) -> str:
    """차이 해시: (size+1)×size 흑백으로 줄인 뒤 옆 픽셀보다 밝으면 1.
    크기·압축·약간의 색 보정이 달라도 같은 사진이면 거의 같은 값이 나온다."""
    small = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(small.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:0{size * size // 4}x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def is_same_photo(a: str, b: str) -> bool:
    return hamming(a, b) <= rules.PHOTO_DUP_DISTANCE


def analyze(data: bytes) -> PhotoInfo:
    if not data:
        raise PhotoError("빈 파일입니다")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        w, h = img.size  # 헤더만 읽은 상태 — 픽셀을 풀기 전에 크기부터 확인 (압축 폭탄 방지)
        if w * h > MAX_PIXELS:
            raise PhotoError("사진 해상도가 너무 커요 (5,000만 화소 이하)")
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise PhotoError("이미지 파일이 아닙니다")
    if fmt not in ALLOWED_FORMATS:
        raise PhotoError("jpg, png, webp 사진만 올릴 수 있어요")

    taken = _taken_at(img)
    img = ImageOps.exif_transpose(img)  # 휴대폰 세로 사진 방향 보정
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")

    if min(img.size) < rules.PHOTO_MIN_SIDE:
        raise PhotoError(f"사진이 너무 작아요 (짧은 변 {rules.PHOTO_MIN_SIDE}px 이상)")
    stat = ImageStat.Stat(img.convert("L"))
    if stat.mean[0] < rules.PHOTO_MIN_BRIGHTNESS:
        raise PhotoError("사진이 너무 어두워요. 밝은 곳에서 다시 찍어 주세요")
    if stat.stddev[0] < rules.PHOTO_MIN_CONTRAST:
        raise PhotoError("사진이 비어 있거나 한 가지 색만 있어요")

    return PhotoInfo(image=img, dhash=dhash(img), taken_at=taken)


def taken_in_period(taken: dt.datetime, start: dt.date, today: dt.date) -> bool:
    tol = dt.timedelta(days=rules.PHOTO_EXIF_TOLERANCE_DAYS)
    return start - tol <= taken.date() <= today + tol


def to_jpeg_bytes(img: Image.Image) -> bytes:
    """축소 + EXIF 제거(위치정보 삭제) 후 JPEG."""
    out = img.copy()
    out.thumbnail((rules.PHOTO_MAX_EDGE, rules.PHOTO_MAX_EDGE))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()
