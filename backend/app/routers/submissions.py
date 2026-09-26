import random
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Submission, SubmissionImage, User
from ..schemas import SubmissionOut, SubmitResult
from ..services.battle import (
    award_streak, entry_closed_message, get_battle_or_404, is_open_for_entries, vote_counts,
)
from ..services.entry_check import (
    check_composition, history_problems, parse_cost, run_ai, same_photo_problem,
)
from ..services.points import award
from ..services.serializers import my_vote_submission_id, submission_out
from ..services.shots import required_shots, shot_guide, shot_label
from ..services.storage import delete_files, inspect_upload, save_photo

router = APIRouter(tags=["submissions"])


@router.get("/battles/{battle_id}/shot-guide")
def shot_guide_for_me(battle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """이번 대결에서 내가 찍어야 할 구도 목록 (참가 화면의 촬영 가이드).
    사용자·대결마다 랜덤 구도가 달라지고, 새로고침해도 같은 결과."""
    battle = get_battle_or_404(db, battle_id)
    return {
        "battle_id": battle.id,
        "verification_keyword": battle.verification_keyword,
        "shots": shot_guide(battle, user),
        "min_side": rules.PHOTO_MIN_SIDE,
        "tips": [
            "구도마다 카메라 위치를 바꿔서 새로 찍어 주세요. 같은 사진을 여러 장 올리면 거절돼요",
            "예전에 올렸던 사진이나 다른 사람 사진은 올릴 수 없어요",
            f"키워드 인증샷에는 '{battle.verification_keyword}'를 종이에 써서 함께 찍어 주세요",
            "휴대폰 카메라로 바로 찍은 원본을 올리면 '촬영 인증' 배지가 붙어요",
        ],
    }


@router.post("/battles/{battle_id}/shot-check")
def shot_check(
    battle_id: int,
    file: UploadFile = File(..., description="검사할 사진 1장"),
    shot: str = Form(..., max_length=20, description="이 사진의 구도 키 (shot-guide의 shot_type)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """구도 칸에 사진을 넣자마자 미리 검사 (저장하지 않음). 참가 화면에서 칸마다 ✅/❌ 표시용.
    같은 사진끼리 비교·'같은 요리인지'는 최종 제출 때 검사한다."""
    battle = get_battle_or_404(db, battle_id)
    if not is_open_for_entries(battle):
        raise HTTPException(status_code=400, detail=entry_closed_message(battle))
    if shot not in required_shots(battle, user):
        raise HTTPException(status_code=400, detail="이번 대결에 필요 없는 구도예요")
    try:
        info = inspect_upload(file, shot_label(shot))
    except HTTPException as e:
        return {"ok": False, "problems": [e.detail], "warnings": [], "ai_status": "skipped",
                "ai_summary": "", "ai_note": "", "time_verified": False}

    problems = history_problems(db, battle, [info], [shot])
    verdict = run_ai(battle, user, [info], [shot])
    if verdict.should_reject:
        problems += verdict.problems
    photos = (verdict.raw or {}).get("photos") or [{}]
    return {
        "ok": not problems,  # true면 이 칸은 ✅
        "problems": problems,  # 제출 시 거절될 문제
        "warnings": verdict.problems if (verdict.status == "failed" and not verdict.should_reject) else [],
        "ai_status": verdict.status,
        "ai_summary": verdict.summary,
        "ai_note": photos[0].get("note", ""),
        "time_verified": info.taken_at is not None,
    }


@router.post("/battles/{battle_id}/submissions", response_model=SubmitResult)
def submit(
    battle_id: int,
    files: list[UploadFile] = File(..., description="구도별 사진. shots와 같은 순서"),
    shots: list[str] = Form(..., description="각 사진의 구도 키 (shot-guide의 shot_type), files와 같은 순서"),
    title: str = Form(..., min_length=1, max_length=40, description="요리명"),
    description: str = Form("", max_length=300),
    ingredient_cost: Optional[str] = Form(None, max_length=20, description="재료비(원, 숫자). 선택"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """대결 참가. 촬영 가이드의 구도를 모두 찍어 올려야 한다. 참가 즉시 +1P.

    검사 순서 (싼 검사 → 비싼 검사): 참가 자격 → 구도 구성 → 사진 형식·품질 → 같은 사진 중복
    → 예전 사진 재사용·촬영 시각 → 이미지 인식 AI (strict면 문제 시 거절)
    """
    battle = get_battle_or_404(db, battle_id)
    if battle.kind != "fail" and battle.group != user.skill:
        raise HTTPException(status_code=403, detail="내 실력 그룹의 대결에만 참가할 수 있어요")
    if not is_open_for_entries(battle):
        raise HTTPException(status_code=400, detail=entry_closed_message(battle))
    if db.query(Submission.id).filter(Submission.battle_id == battle_id, Submission.user_id == user.id).first():
        raise HTTPException(status_code=400, detail="이미 참가한 대결입니다")

    shots = [x.strip() for x in shots]
    check_composition(battle, user, shots, len(files))
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="요리명을 입력해 주세요")
    cost = parse_cost(ingredient_cost)

    infos = [inspect_upload(f, shot_label(k)) for f, k in zip(files, shots)]
    problem = same_photo_problem(infos, shots)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    problems = history_problems(db, battle, infos, shots)
    if problems:
        raise HTTPException(status_code=400, detail=problems[0])
    verdict = run_ai(battle, user, infos, shots)
    if verdict.should_reject:
        raise HTTPException(status_code=400, detail="AI 사진 검사를 통과하지 못했어요: " + " / ".join(verdict.problems))

    # 저장 (EXIF·위치정보 제거된 JPEG). 중간에 실패하면 저장한 파일 정리
    paths = []
    try:
        for info in infos:
            paths.append(save_photo(info))
        sub = Submission(
            battle_id=battle_id, user_id=user.id, title=title, description=description.strip(),
            ingredient_cost=cost, ai_status=verdict.status, ai_result=verdict.to_dict(),
            images=[
                SubmissionImage(path=p, position=i, shot_type=k, phash=info.dhash, taken_at=info.taken_at)
                for i, (p, k, info) in enumerate(zip(paths, shots, infos))
            ],
        )
        db.add(sub)
        db.flush()
        level_before, total_before = user.level, user.total_points
        award(db, user, rules.PARTICIPATION_POINTS, "participation", f"battle:{battle.id}",
              memo=f"'{battle.category.name}' 대결 참가")
        award(db, user, rules.FIRST_BATTLE_BONUS, "first_battle", "once", memo="첫 대결 참가 보너스")
        award_streak(db, user, battle)
        db.commit()
    except IntegrityError:  # 동시에 두 번 제출
        db.rollback()
        delete_files(paths)
        raise HTTPException(status_code=400, detail="이미 참가한 대결입니다")
    except Exception:
        db.rollback()
        delete_files(paths)
        raise
    db.refresh(sub)
    db.refresh(user)
    return SubmitResult(
        submission=submission_out(sub, db, user, 0, None),
        points_earned=user.total_points - total_before,
        level=user.level,
        leveled_up=user.level > level_before,
    )


@router.get("/battles/{battle_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(battle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """출품작 목록. 순서는 사용자마다 랜덤(새로고침해도 유지). 숨김 작품은 본인에게만 보임."""
    battle = get_battle_or_404(db, battle_id)
    subs = [
        s for s in db.query(Submission).filter(Submission.battle_id == battle.id).order_by(Submission.id).all()
        if not s.is_hidden or s.user_id == user.id
    ]
    random.Random(f"{user.id}:{battle.id}").shuffle(subs)
    counts = vote_counts(db, battle.id)
    my_vote = my_vote_submission_id(db, battle.id, user)
    return [submission_out(s, db, user, counts.get(s.id, 0), my_vote) for s in subs]


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if s is None or (s.is_hidden and s.user_id != user.id):
        raise HTTPException(status_code=404, detail="작품을 찾을 수 없습니다")
    counts = vote_counts(db, s.battle_id)
    return submission_out(s, db, user, counts.get(s.id, 0), my_vote_submission_id(db, s.battle_id, user))
