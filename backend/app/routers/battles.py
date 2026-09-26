from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Battle, Recipe, Submission, User
from ..schemas import BattleOut, BattleResults, MyResult, ResultEntry
from ..services.battle import (
    battle_points_for_user, close_expired_battles, compute_rankings, get_battle_or_404, get_or_start_battle,
)
from ..services.serializers import battle_out
from ..services.storage import to_url

router = APIRouter(prefix="/battles", tags=["battles"])


@router.get("/current", response_model=BattleOut)
def current_battle(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """내 실력 그룹의 진행 중 대결. 없으면 랜덤 카테고리로 새 대결이 자동으로 열린다."""
    return battle_out(get_or_start_battle(db, user.skill), db, user)


@router.get("/fail/current", response_model=BattleOut)
def current_fail_battle(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """'망한 요리 대회' — 리그 구분 없이 누구나 참가. 리그 대결과 따로 동시에 진행된다."""
    if not rules.FAIL_CONTEST_ENABLED:
        raise HTTPException(status_code=404, detail="망한 요리 대회가 열려 있지 않아요")
    return battle_out(get_or_start_battle(db, rules.FAIL_GROUP), db, user)


@router.get("/active", response_model=list[BattleOut])
def all_active_battles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """진행 중인 모든 대결: 리그(하/중/상) + 망한 요리 대회 — 다른 대결 구경용 (투표는 참가자만)."""
    groups = list(rules.LEAGUE_GROUPS) + ([rules.FAIL_GROUP] if rules.FAIL_CONTEST_ENABLED else [])
    return [battle_out(get_or_start_battle(db, g), db, user) for g in groups]


@router.get("/history", response_model=list[BattleOut])
def battle_history(
    mine: bool = False,
    group: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """마감된 대결 목록. mine=true면 내가 참가한 대결만, group으로 그룹 필터."""
    close_expired_battles(db)
    q = db.query(Battle).filter(Battle.is_closed.is_(True))
    if group:
        q = q.filter(Battle.group == group)
    if mine:
        q = q.join(Submission, Submission.battle_id == Battle.id).filter(Submission.user_id == user.id)
    battles = q.order_by(Battle.closed_at.desc(), Battle.id.desc()).limit(limit).all()
    return [battle_out(b, db, user) for b in battles]


@router.get("/{battle_id}", response_model=BattleOut)
def get_battle(battle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return battle_out(get_battle_or_404(db, battle_id), db, user)


def _entry(e, recipe_id=None) -> ResultEntry:
    s = e.submission
    return ResultEntry(
        submission_id=s.id, user_id=s.user_id, nickname=s.user.nickname, title=s.title,
        image_url=to_url(s.images[0].path) if s.images else "",
        vote_count=e.votes, rank=e.rank, rank_points=e.rank_points, recipe_id=recipe_id,
    )


@router.get("/{battle_id}/results", response_model=BattleResults)
def battle_results(battle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """대결 결과: 1~3등 시상대, 전체 순위, 내 순위·획득 포인트·레벨업 여부. 마감 후에만 조회 가능."""
    battle = get_battle_or_404(db, battle_id)
    if not battle.is_closed:
        raise HTTPException(status_code=400, detail="대결이 끝난 뒤에 결과를 볼 수 있어요")

    entries = compute_rankings(db, battle)
    shared = dict(
        db.query(Recipe.source_submission_id, Recipe.id)
        .filter(Recipe.source_submission_id.in_([e.submission.id for e in entries] or [0]))
        .all()
    )
    ranked = [_entry(e, shared.get(e.submission.id)) for e in entries]
    podium = [] if battle.is_void else [r for r in ranked if r.rank <= 3 and r.vote_count > 0]

    my_result = None
    mine = next((e for e in entries if e.submission.user_id == user.id), None)
    if mine is not None:
        pts = battle_points_for_user(db, battle.id, user.id)
        my_result = MyResult(
            submission_id=mine.submission.id,
            rank=mine.rank,
            # 레시피 공유는 리그 대결 우승자만 (망한 요리 레시피는 공유하지 않음)
            can_share_recipe=(battle.kind != "fail" and not battle.is_void and mine.rank == 1 and mine.votes > 0),
            **pts,
        )
    return BattleResults(
        battle=battle_out(battle, db, user), is_void=battle.is_void,
        podium=podium, entries=ranked, my_result=my_result,
    )
