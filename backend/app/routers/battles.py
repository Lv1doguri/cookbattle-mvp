from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .. import clock
from ..content import WEEKDAY_LABELS, WEEKLY_THEMES
from ..database import get_db
from ..enums import TIER_LABEL, Tier
from ..errors import ApiError
from ..models import Battle, Post, User
from ..schemas import (
    BattleOut,
    LeaderboardEntry,
    LeaderboardMe,
    LeaderboardOut,
    MyEntryOut,
    WeeklyThemeOut,
)
from ..security import get_current_user
from ..services.battles import get_or_create_battle
from ..services.serialize import count, user_brief

router = APIRouter(prefix="/battles", tags=["battles"])


def _ranked_ahead_of(mine: Post):
    """Ranking: higher score first; ties go to the earlier entry."""
    return or_(
        Post.battle_score > mine.battle_score,
        and_(
            Post.battle_score == mine.battle_score,
            or_(
                Post.created_at < mine.created_at,
                and_(Post.created_at == mine.created_at, Post.id < mine.id),
            ),
        ),
    )


def _my_rank(db: Session, battle_id: int, mine: Post) -> int:
    return count(db, Post, Post.battle_id == battle_id, _ranked_ahead_of(mine)) + 1


@router.get("/today", response_model=BattleOut)
def today_battle(
    tier: Optional[Tier] = Query(None, description="생략하면 내 실력 단계"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """오늘의 대결. 탭(초급/중급/고급)마다 tier를 바꿔 호출하세요. 내 단계가 아닌 탭은 can_join=false."""
    now = clock.utcnow()
    today = clock.kst_date(now)
    battle = get_or_create_battle(db, tier or user.tier or Tier.beginner, today)

    mine = db.scalar(select(Post).where(Post.battle_id == battle.id, Post.author_id == user.id))
    is_my_tier = user.tier == battle.tier
    is_open = battle.starts_at <= now < battle.ends_at
    return BattleOut(
        id=battle.id,
        date=battle.date,
        tier=battle.tier,
        tier_label=TIER_LABEL[battle.tier],
        theme=battle.theme,
        description=battle.description,
        reward_xp=battle.reward_xp,
        reward_coins=battle.reward_coins,
        starts_at=battle.starts_at,
        ends_at=battle.ends_at,
        seconds_left=max(0, int((battle.ends_at - now).total_seconds())),
        server_time=now,
        participants=count(db, Post, Post.battle_id == battle.id),
        is_my_tier=is_my_tier,
        can_join=is_my_tier and is_open and mine is None,
        my_entry=(
            MyEntryOut(post_id=mine.id, xp=mine.battle_score, rank=_my_rank(db, battle.id, mine)) if mine else None
        ),
        weekly_challenge=[
            WeeklyThemeOut(weekday=WEEKDAY_LABELS[i], theme=sched["theme"], is_today=i == today.weekday())
            for i, sched in enumerate(WEEKLY_THEMES)
        ],
    )


@router.get("/{battle_id}/leaderboard", response_model=LeaderboardOut)
def leaderboard(
    battle_id: int,
    limit: int = Query(50, ge=1, le=100, description="홈/대결 화면 미리보기는 2, 전체 보기는 100"),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    battle = db.get(Battle, battle_id)
    if battle is None:
        raise ApiError(404, "battle_not_found", "대결을 찾을 수 없습니다")

    rows = db.execute(
        select(Post, User)
        .join(User, User.id == Post.author_id)
        .where(Post.battle_id == battle_id)
        .order_by(Post.battle_score.desc(), Post.created_at.asc(), Post.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    entries = [
        LeaderboardEntry(
            rank=offset + i + 1,
            user=user_brief(author),
            xp=post.battle_score,
            post_id=post.id,
            is_me=author.id == user.id,
        )
        for i, (post, author) in enumerate(rows)
    ]

    me = None
    mine = db.scalar(select(Post).where(Post.battle_id == battle_id, Post.author_id == user.id))
    if mine is not None:
        rank = _my_rank(db, battle_id, mine)
        xp_to_next = 0
        if rank > 1:
            above = db.scalar(
                select(Post)
                .where(Post.battle_id == battle_id, _ranked_ahead_of(mine))
                .order_by(Post.battle_score.asc(), Post.created_at.desc(), Post.id.desc())
                .limit(1)
            )
            gap = above.battle_score - mine.battle_score
            i_win_ties = (mine.created_at, mine.id) < (above.created_at, above.id)
            xp_to_next = gap if i_win_ties else gap + 1
        me = LeaderboardMe(rank=rank, xp=mine.battle_score, xp_to_next_rank=xp_to_next)

    return LeaderboardOut(
        battle_id=battle.id,
        tier=battle.tier,
        tier_label=TIER_LABEL[battle.tier],
        theme=battle.theme,
        participants=count(db, Post, Post.battle_id == battle_id),
        entries=entries,
        me=me,
    )
