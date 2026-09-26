"""대결 참가 사진 검사 모음 — 참가(submit)와 미리 검사(shot-check)가 같이 쓴다."""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import rules
from ..models import Battle, SubmissionImage, User
from ..timeutil import today
from . import ratelimit
from .ai_vision import AIVerdict, check_photos, is_enabled
from .photo_check import is_same_photo, taken_in_period
from .shots import required_shots, shot_label


def check_composition(battle: Battle, user: User, shots: list, file_count: int) -> None:
    """촬영 가이드의 구도를 빠짐없이, 한 번씩만 올렸는지."""
    if file_count != len(shots):
        raise HTTPException(status_code=400, detail="사진 수와 구도 정보 수가 달라요")
    required = required_shots(battle, user)
    unknown = [x for x in shots if x not in required]
    if unknown:
        raise HTTPException(status_code=400, detail=f"이번 대결에 필요 없는 구도예요: {', '.join(unknown)}")
    dup = next((x for x in shots if shots.count(x) > 1), None)
    if dup:
        raise HTTPException(status_code=400, detail=f"'{shot_label(dup)}' 구도가 두 번 들어갔어요")
    missing = [x for x in required if x not in shots]
    if missing:
        raise HTTPException(status_code=400, detail="필요한 사진이 빠졌어요: " + ", ".join(shot_label(x) for x in missing))


def same_photo_problem(infos: list, shots: list) -> Optional[str]:
    """한 번에 올린 사진끼리 같은 사진인지 (구도를 안 바꾸고 여러 장)."""
    for i in range(len(infos)):
        for j in range(i + 1, len(infos)):
            if is_same_photo(infos[i].dhash, infos[j].dhash):
                return (f"'{shot_label(shots[i])}'와 '{shot_label(shots[j])}' 사진이 같은 사진이에요. "
                        "구도를 바꿔서 다시 찍어 주세요")
    return None


def history_problems(db: Session, battle: Battle, infos: list, shots: list) -> list:
    """예전에 올라온 사진 재사용 / 대결 기간이 아닐 때 찍은 사진."""
    problems = []
    past = [h for (h,) in db.query(SubmissionImage.phash).filter(SubmissionImage.phash.isnot(None)).all()]
    for info, k in zip(infos, shots):
        if any(is_same_photo(info.dhash, h) for h in past):
            problems.append(f"'{shot_label(k)}' 사진은 이미 올라온 적 있는 사진이에요. 새로 찍어 주세요")
        if info.taken_at and not taken_in_period(info.taken_at, battle.start_date, today()):
            problems.append(f"'{shot_label(k)}' 사진은 대결 기간이 아닐 때 찍은 사진이에요 (촬영일 {info.taken_at:%Y-%m-%d})")
    return problems


def run_ai(battle: Battle, user: User, infos: list, shots: list) -> AIVerdict:
    """이미지 인식 AI. 사용자당 시간당 호출 수 제한 (유료 API 남용 방지)."""
    if is_enabled():
        ratelimit.hit(f"ai:{user.id}", rules.AI_CALLS_PER_HOUR, 3600, "사진 AI 검사 요청이 너무 많아요")
    return check_photos(
        [i.image for i in infos], shots, [shot_label(k) for k in shots],
        battle.verification_keyword, battle.category.name, fail_contest=battle.kind == "fail",
    )


def parse_cost(raw: Optional[str]) -> Optional[int]:
    if raw is None or not raw.strip():
        return None
    try:
        cost = int(raw.replace(",", "").replace("원", "").strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="재료비는 숫자로 입력해 주세요")
    if not 0 <= cost <= 1_000_000:
        raise HTTPException(status_code=400, detail="재료비는 0 ~ 1,000,000원 사이로 입력해 주세요")
    return cost
