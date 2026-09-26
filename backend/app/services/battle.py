"""대결 생성(랜덤 카테고리), 순위 계산, 마감(포인트 지급) 로직."""
import datetime as dt
import random
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..models import Battle, Category, PointLog, Submission, User, Vote
from ..timeutil import today, utcnow
from .points import award


# ---------- 생성 / 조회 ----------

def active_battle(db: Session, group: str) -> Optional[Battle]:
    d = today()
    return (
        db.query(Battle)
        .filter(Battle.group == group, Battle.is_closed.is_(False), Battle.start_date <= d, Battle.end_date >= d)
        .order_by(Battle.id.desc())
        .first()
    )


def kind_of(group: str) -> str:
    return "fail" if group == rules.FAIL_GROUP else "league"


def start_battle(db: Session, group: str, category_id: Optional[int] = None) -> Battle:
    """새 대결 시작 (리그: 요리 1일+투표 1일 / 망한 요리 대회: 요리 3일+투표 1일).
    category_id가 없으면 같은 종류(리그/망한 요리) 주제 중 직전 것을 피해 랜덤 선택."""
    kind = kind_of(group)
    if category_id is not None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category is None:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
    else:
        pool = db.query(Category).filter(Category.is_active.is_(True), Category.kind == kind).all()
        if not pool and kind == "fail":  # 예전 DB라 망한 요리 주제가 없으면 기본 주제를 만들어 사용
            default = Category(name="망한 요리 자랑", description="처참하게 망한 요리를 자랑해 주세요", kind="fail")
            db.add(default)
            db.flush()
            pool = [default]
        if not pool:
            raise HTTPException(status_code=500, detail="등록된 대결 카테고리가 없습니다 (seed를 실행하세요)")
        last = db.query(Battle).filter(Battle.group == group).order_by(Battle.id.desc()).first()
        candidates = [c for c in pool if not last or c.id != last.category_id] or pool
        category = random.choice(candidates)

    start = today()
    cooking_days = rules.cooking_days_for(kind)
    duration_days = rules.duration_days_for(kind)
    battle = Battle(
        group=group,
        kind=kind,
        category_id=category.id,
        start_date=start,
        vote_start_date=start + dt.timedelta(days=cooking_days),
        end_date=start + dt.timedelta(days=duration_days - 1),
        verification_keyword=random.choice(rules.VERIFICATION_KEYWORDS),
    )
    db.add(battle)
    try:
        db.commit()
    except IntegrityError:  # 동시 요청으로 다른 요청이 먼저 대결을 열었음 → 그 대결을 사용
        db.rollback()
        existing = active_battle(db, group)
        if existing is None:
            raise
        return existing
    db.refresh(battle)
    return battle


def get_or_start_battle(db: Session, group: str) -> Battle:
    """그룹의 진행 중 대결. 없으면(첫 실행이거나 직전 대결이 끝났으면) 랜덤 카테고리로 새로 연다."""
    close_expired_battles(db)
    return active_battle(db, group) or start_battle(db, group)


def get_battle_or_404(db: Session, battle_id: int) -> Battle:
    close_expired_battles(db)
    battle = db.query(Battle).filter(Battle.id == battle_id).first()
    if battle is None:
        raise HTTPException(status_code=404, detail="대결을 찾을 수 없습니다")
    return battle


def is_open_for_entries(battle: Battle) -> bool:
    """사진 올리기는 요리 기간에만."""
    return battle.phase == "cooking" and battle.start_date <= today()


def entry_closed_message(battle: Battle) -> str:
    if battle.phase == "voting":
        return f"요리 기간이 끝났어요. 지금은 투표 기간이에요 (~{battle.end_date:%m/%d})"
    return "이미 끝난 대결입니다"


def days_left(battle: Battle) -> int:
    """대결 전체 종료까지 남은 날 (마지막 날 0)."""
    if battle.is_closed:
        return 0
    return max((battle.end_date - today()).days, 0)


def phase_days_left(battle: Battle) -> int:
    """지금 단계(요리/투표)가 끝날 때까지 남은 날 (마지막 날 0)."""
    if battle.phase == "cooking":
        return max((battle.voting_starts - dt.timedelta(days=1) - today()).days, 0)
    return days_left(battle)


def my_entry(db: Session, battle: Battle, user: User) -> Optional[Submission]:
    return db.query(Submission).filter(Submission.battle_id == battle.id, Submission.user_id == user.id).first()


def vote_block_reason(db: Session, battle: Battle, user: User) -> Optional[str]:
    """투표할 수 없는 이유 (없으면 None = 투표 가능). 투표는 그 대결 참가자만, 투표 기간에만."""
    if battle.phase == "closed":
        return "이미 끝난 대결입니다"
    if battle.phase == "cooking":
        return f"투표는 {battle.voting_starts:%m/%d}부터 시작해요 (지금은 요리 기간)"
    entry = my_entry(db, battle, user)
    if entry is None:
        return "이 대결에 참가한 사람만 투표할 수 있어요"
    if entry.is_hidden:
        return "내 작품이 신고로 숨김 처리되어 투표할 수 없어요"
    if db.query(Vote.id).filter(Vote.battle_id == battle.id, Vote.voter_id == user.id).first():
        return "이미 투표하셨습니다"
    return None


def set_phase(db: Session, battle: Battle, phase: str) -> None:
    """[관리자/시연용] 날짜를 조정해 지금 바로 요리 기간 또는 투표 기간으로 만든다."""
    d = today()
    if phase == "voting":
        battle.vote_start_date = d
        if battle.end_date < d:
            battle.end_date = d
    elif phase == "cooking":
        battle.vote_start_date = d + dt.timedelta(days=1)
        if battle.end_date < battle.vote_start_date:
            battle.end_date = battle.vote_start_date
    else:
        raise HTTPException(status_code=400, detail="phase는 cooking 또는 voting")
    db.commit()


# ---------- 순위 ----------

@dataclass
class RankedEntry:
    submission: Submission
    votes: int = 0
    rank: int = 0
    rank_points: int = 0


def vote_counts(db: Session, battle_id: int) -> dict:
    rows = (
        db.query(Vote.submission_id, func.count(Vote.id))
        .filter(Vote.battle_id == battle_id)
        .group_by(Vote.submission_id)
        .all()
    )
    return {sid: n for sid, n in rows}


def compute_rankings(db: Session, battle: Battle) -> list:
    """득표순, 동점이면 먼저 제출한 사람 우선. 숨김 작품 제외.
    무효 대결이면 순위 포인트 없음. 참가자가 RANK_FULL_MIN_PARTICIPANTS 미만이면 순위 포인트 절반만
    (계정 여러 개로 순위를 나눠 먹는 걸 막는 안전장치)."""
    subs = (
        db.query(Submission)
        .filter(Submission.battle_id == battle.id, Submission.is_hidden.is_(False))
        .all()
    )
    counts = vote_counts(db, battle.id)
    entries = [RankedEntry(submission=s, votes=counts.get(s.id, 0)) for s in subs]
    entries.sort(key=lambda e: (-e.votes, e.submission.created_at, e.submission.id))
    table = rules.FAIL_RANK_POINTS if battle.kind == "fail" else rules.RANK_POINTS
    half = len(entries) < rules.RANK_FULL_MIN_PARTICIPANTS
    for i, e in enumerate(entries):
        e.rank = i + 1
        if not battle.is_void and i < len(table) and e.votes > 0:
            e.rank_points = table[i] // 2 if half else table[i]
    return entries


def is_winner(db: Session, submission: Submission) -> bool:
    battle = submission.battle
    if not battle.is_closed or battle.is_void:
        return False
    entries = compute_rankings(db, battle)
    return bool(entries) and entries[0].submission.id == submission.id and entries[0].votes > 0


# ---------- 마감 ----------

def close_battle(db: Session, battle: Battle) -> None:
    """마감 + 순위 포인트 지급. 참가자가 MIN_PARTICIPANTS 미만이면 무효 (참가 포인트는 이미 지급됨)."""
    if battle.is_closed:
        return
    participants = (
        db.query(Submission)
        .filter(Submission.battle_id == battle.id, Submission.is_hidden.is_(False))
        .count()
    )
    battle.is_closed = True
    battle.closed_at = utcnow()
    battle.is_void = participants < rules.MIN_PARTICIPANTS

    if not battle.is_void:
        for e in compute_rankings(db, battle):
            if e.rank_points:
                award(
                    db, e.submission.user, e.rank_points, "rank", f"battle:{battle.id}",
                    memo=f"'{battle.category.name}' 대결 {e.rank}등",
                )
    db.commit()


def close_expired_battles(db: Session) -> int:
    expired = db.query(Battle).filter(Battle.is_closed.is_(False), Battle.end_date < today()).all()
    for b in expired:
        close_battle(db, b)
    return len(expired)


# ---------- 포인트 보조 ----------

def _iso_week(d: dt.date) -> tuple:
    y, w, _ = d.isocalendar()
    return (y, w)


def award_streak(db: Session, user: User, battle: Battle) -> None:
    """[Could] 이번 주 포함 N주 연속 참가 시 보너스 (주당 1회)."""
    if rules.STREAK_BONUS <= 0:
        return
    dates = (
        db.query(Battle.start_date)
        .join(Submission, Submission.battle_id == Battle.id)
        .filter(Submission.user_id == user.id)
        .all()
    )
    weeks = {_iso_week(d) for (d,) in dates}
    current = _iso_week(battle.start_date)
    streak, wk = 0, current
    while wk in weeks:
        streak += 1
        monday = dt.date.fromisocalendar(wk[0], wk[1], 1)
        wk = _iso_week(monday - dt.timedelta(days=7))
    if streak >= rules.STREAK_WEEKS and streak % rules.STREAK_WEEKS == 0:
        award(db, user, rules.STREAK_BONUS, "streak", f"week:{current[0]}-{current[1]:02d}",
              memo=f"{streak}주 연속 참가 보너스")


def battle_points_for_user(db: Session, battle_id: int, user_id: int) -> dict:
    """이 대결로 얻은 포인트와, 순위 포인트 지급 전후 레벨 (레벨업 팝업용)."""
    logs = (
        db.query(PointLog)
        .filter(PointLog.user_id == user_id, PointLog.ref == f"battle:{battle_id}")
        .all()
    )
    earned = sum(l.points for l in logs)
    rank_log = next((l for l in logs if l.reason == "rank"), None)
    if rank_log is None:
        return {"points_earned": earned, "level_before": None, "level_after": None, "leveled_up": False}
    before_total = (
        db.query(func.coalesce(func.sum(PointLog.points), 0))
        .filter(PointLog.user_id == user_id, PointLog.id < rank_log.id)
        .scalar()
    )
    lb = rules.level_for(before_total)
    la = rules.level_for(before_total + rank_log.points)
    return {"points_earned": earned, "level_before": lb, "level_after": la, "leveled_up": la > lb}
