import datetime as dt
import random
from typing import List, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import clock
from ..content import (
    ANGLE_BY_ID,
    BATTLE_EPOCH,
    BATTLE_THEMES,
    MIN_PARTICIPANTS,
    RANK_FULL_MIN_PARTICIPANTS,
    RANK_POINTS,
    STREAK_BONUS,
    STREAK_WEEKS,
    THEME_BATTLES,
    THEME_COOKING_DAYS,
    THEME_EPOCH,
    VOTING_WINDOW,
)
from ..enums import BattleKind, BattlePhase, Tier
from ..models import Battle, Entry, User
from ..schemas import EntryOut
from .accounts import user_brief
from .images import image_url
from .points import grant_points, level_for


def battle_title(battle: Battle) -> str:
    """'계란 요리 대결'(daily) 이지만, 테마 대결 이름은 이미 '~대회'로 끝나서 그대로 써요
    (예: '망한 요리 대회' — '망한 요리 대회 대결'이 되지 않게)."""
    if battle.kind == BattleKind.theme:
        return battle.theme
    return f"{battle.theme} 대결"


def week_label(week_start: dt.date) -> str:
    """'9월 3주차'. A week belongs to the month its Thursday falls in, so labels never straddle months."""
    anchor = week_start + dt.timedelta(days=3)
    return f"{anchor.month}월 {(anchor.day - 1) // 7 + 1}주차"


def phase(battle: Battle, now: dt.datetime) -> BattlePhase:
    if now < battle.ends_at:
        return BattlePhase.cooking
    if now < battle.voting_ends_at:
        return BattlePhase.voting
    return BattlePhase.closed


def is_open(battle: Battle, now: dt.datetime) -> bool:
    """Still in the cooking (참가 가능) period."""
    return phase(battle, now) == BattlePhase.cooking


def can_vote_now(battle: Battle, now: dt.datetime) -> bool:
    """대회가 끝난 뒤 24시간(VOTING_WINDOW) 동안만 투표할 수 있어요."""
    return phase(battle, now) == BattlePhase.voting


def _ensure_required_angle(db: Session, battle: Battle) -> None:
    """Self-heals a battle created before the angle-photo feature existed."""
    if battle.required_angle is None:
        battle.required_angle = random.choice(list(ANGLE_BY_ID))
        db.commit()


def get_or_create_daily_battle(db: Session, tier: Tier, now: dt.datetime) -> Battle:
    """'오늘의 대결': the battle for this KST week and skill group. Created lazily on first request.

    Commits when it creates, so only call it where the session has no other pending work.
    """
    week_start = clock.kst_week_start(clock.kst_date(now))
    stmt = select(Battle).where(Battle.kind == BattleKind.daily, Battle.week_start == week_start, Battle.tier == tier)
    battle = db.scalar(stmt)
    if battle is not None:
        _ensure_required_angle(db, battle)
        return battle

    schedule = BATTLE_THEMES[((week_start - BATTLE_EPOCH).days // 7) % len(BATTLE_THEMES)]
    db.add(
        Battle(
            kind=BattleKind.daily,
            tier=tier,
            theme=schedule["theme"],
            description=schedule[tier],
            week_start=week_start,
            starts_at=clock.kst_day_bounds(week_start)[0],
            ends_at=clock.kst_day_bounds(week_start + dt.timedelta(days=7))[0],
            voting_ends_at=clock.kst_day_bounds(week_start + dt.timedelta(days=7))[0] + VOTING_WINDOW,
            required_angle=random.choice(list(ANGLE_BY_ID)),
        )
    )
    try:
        db.commit()
    except IntegrityError:  # another request created it first
        db.rollback()
    return db.scalar(stmt)


def get_or_create_theme_battle(db: Session, now: dt.datetime) -> Battle:
    """'테마 대결': one shared battle for every skill group (tier is null).

    설계에 그룹별인지 전체 공통인지가 정해져 있지 않아서 "전체 공통"으로 가정했어요
    (API_CONTRACT.md 참고). 요일별 대결과 달리 주 단위가 아니라 THEME_COOKING_DAYS 주기로 돌아가요.
    """
    today = clock.kst_date(now)
    cycle_index = (today - THEME_EPOCH).days // THEME_COOKING_DAYS
    cycle_start = THEME_EPOCH + dt.timedelta(days=cycle_index * THEME_COOKING_DAYS)

    stmt = select(Battle).where(Battle.kind == BattleKind.theme, Battle.week_start == cycle_start)
    battle = db.scalar(stmt)
    if battle is not None:
        _ensure_required_angle(db, battle)
        return battle

    schedule = THEME_BATTLES[cycle_index % len(THEME_BATTLES)]
    starts_at = clock.kst_day_bounds(cycle_start)[0]
    ends_at = clock.kst_day_bounds(cycle_start + dt.timedelta(days=THEME_COOKING_DAYS))[0]
    db.add(
        Battle(
            kind=BattleKind.theme,
            tier=None,
            theme=schedule["theme"],
            description=schedule["description"],
            week_start=cycle_start,
            starts_at=starts_at,
            ends_at=ends_at,
            voting_ends_at=ends_at + VOTING_WINDOW,
            required_angle=random.choice(list(ANGLE_BY_ID)),
        )
    )
    try:
        db.commit()
    except IntegrityError:  # another request created it first
        db.rollback()
    return db.scalar(stmt)


def award_streak(db: Session, user: User, battle: Battle) -> None:
    """STREAK_WEEKS 연속으로 '오늘의 대결'(daily)에 참가하면 매 STREAK_WEEKS번째 주에 보너스.
    망한 요리 같은 테마 대결은 주간 주기가 아니라서 집계에서 빠져요."""
    if battle.kind != BattleKind.daily or STREAK_BONUS <= 0:
        return
    weeks_joined = set(
        db.scalars(
            select(Battle.week_start)
            .join(Entry, Entry.battle_id == Battle.id)
            .where(Entry.user_id == user.id, Battle.kind == BattleKind.daily)
        ).all()
    )
    streak, wk = 0, battle.week_start
    while wk in weeks_joined:
        streak += 1
        wk -= dt.timedelta(days=7)
    if streak >= STREAK_WEEKS and streak % STREAK_WEEKS == 0:
        grant_points(db, user, STREAK_BONUS, reason="streak", ref_type="battle", ref_id=battle.id)


def find_voting_battle(db: Session, kind: BattleKind, tier: Optional[Tier], now: dt.datetime) -> Optional[Battle]:
    """The most recent battle of this kind/tier that's currently in its 24-hour voting window."""
    stmt = select(Battle).where(
        Battle.kind == kind,
        Battle.ends_at <= now,
        Battle.voting_ends_at > now,
    )
    stmt = stmt.where(Battle.tier == tier) if tier is not None else stmt.where(Battle.tier.is_(None))
    return db.scalar(stmt.order_by(Battle.ends_at.desc()))


def ranked_entries(db: Session, battle_id: int) -> Sequence[Entry]:
    """Most votes first; on a tie, whoever submitted first ranks higher."""
    return db.scalars(
        select(Entry)
        .options(joinedload(Entry.user))
        .where(Entry.battle_id == battle_id)
        .order_by(Entry.vote_count.desc(), Entry.created_at.asc(), Entry.id.asc())
    ).all()


def finalize_due_battles(db: Session, now: dt.datetime) -> None:
    """Hand out ranks and rank points for every battle whose voting window has closed.

    There is no scheduler: whichever request comes first after voting ends does it. It is
    idempotent and safe under concurrency (see _finalize).
    """
    due = db.scalars(select(Battle.id).where(Battle.finalized_at.is_(None), Battle.voting_ends_at <= now)).all()
    for battle_id in due:
        _finalize(db, battle_id, now)


def _finalize(db: Session, battle_id: int, now: dt.datetime) -> None:
    # Claiming the battle is one conditional UPDATE, so if two requests race only one gets rowcount 1.
    claimed = db.execute(
        update(Battle).where(Battle.id == battle_id, Battle.finalized_at.is_(None)).values(finalized_at=now)
    )
    if claimed.rowcount != 1:
        db.rollback()
        return

    entries = ranked_entries(db, battle_id)
    if len(entries) < MIN_PARTICIPANTS:
        db.execute(update(Battle).where(Battle.id == battle_id).values(is_void=True))
    else:
        # Fewer than RANK_FULL_MIN_PARTICIPANTS participants -> rank points are halved (stops a
        # handful of alt accounts from splitting the full reward among themselves).
        half = len(entries) < RANK_FULL_MIN_PARTICIPANTS
        for rank, entry in enumerate(entries, start=1):
            user = db.get(User, entry.user_id)
            level_from = level_for(user.total_points)
            reward = RANK_POINTS.get(rank, 0)
            if half:
                reward //= 2
            if reward:
                grant_points(db, user, reward, reason="rank_reward", ref_type="entry", ref_id=entry.id)
            entry.rank = rank
            entry.rank_points = reward
            entry.level_from = level_from
            entry.level_to = level_for(user.total_points)
    db.commit()


def entry_state(entry: Entry, viewer_id: int, my_vote_entry_id: Optional[int], can_vote: bool) -> str:
    if entry.user_id == viewer_id:
        return "mine"
    if my_vote_entry_id is not None:
        return "voted" if entry.id == my_vote_entry_id else "vote_done"
    return "votable" if can_vote else "unavailable"


def _rating_stats(overall_ratings: Sequence[float]) -> tuple:
    if not overall_ratings:
        return None, 0
    return round(sum(overall_ratings) / len(overall_ratings), 1), len(overall_ratings)


def entry_out(entry: Entry, state: str, ratings: Sequence[int] = ()) -> EntryOut:
    avg, n = _rating_stats(ratings)
    return EntryOut(
        id=entry.id,
        battle_id=entry.battle_id,
        dish_name=entry.dish_name,
        description=entry.description,
        photo_url=image_url(entry.photo.filename),
        angle_photo_url=image_url(entry.angle_photo.filename) if entry.angle_photo else None,
        author=user_brief(entry.user),
        vote_count=entry.vote_count,
        created_at=entry.created_at,
        state=state,
        notify_on_close=entry.notify_on_close,
        comment_count=n,
        rating_avg=avg,
        rating_count=n,
    )


def entry_outs(
    db: Session, entries: Sequence[Entry], viewer_id: int, my_vote_entry_id: Optional[int], can_vote: bool
) -> List[EntryOut]:
    from ..models import EntryComment  # local import: avoids a circular import at module load time

    ratings_by_entry: dict = {}
    if entries:
        rows = db.execute(
            select(EntryComment.entry_id, EntryComment.visual_rating, EntryComment.value_rating).where(
                EntryComment.entry_id.in_([e.id for e in entries])
            )
        )
        for entry_id, visual, value in rows:
            ratings_by_entry.setdefault(entry_id, []).append((visual + value) / 2)
    return [
        entry_out(e, entry_state(e, viewer_id, my_vote_entry_id, can_vote), ratings_by_entry.get(e.id, []))
        for e in entries
    ]
