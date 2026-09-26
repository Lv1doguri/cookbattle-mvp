import datetime as dt
from typing import List, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import clock
from ..content import BATTLE_EPOCH, BATTLE_THEMES, MIN_PARTICIPANTS, RANK_POINTS
from ..enums import Tier
from ..models import Battle, Entry, User
from ..schemas import EntryOut
from .accounts import user_brief
from .images import image_url
from .points import grant_points, level_for


def battle_title(theme: str) -> str:
    return f"{theme} 대결"


def week_label(week_start: dt.date) -> str:
    """'9월 3주차'. A week belongs to the month its Thursday falls in, so labels never straddle months."""
    anchor = week_start + dt.timedelta(days=3)
    return f"{anchor.month}월 {(anchor.day - 1) // 7 + 1}주차"


def is_open(battle: Battle, now: dt.datetime) -> bool:
    return battle.starts_at <= now < battle.ends_at


def get_or_create_battle(db: Session, tier: Tier, now: dt.datetime) -> Battle:
    """The battle for this KST week and group. Created lazily on first request.

    Commits when it creates, so only call it where the session has no other pending work.
    """
    week_start = clock.kst_week_start(clock.kst_date(now))
    stmt = select(Battle).where(Battle.week_start == week_start, Battle.tier == tier)
    battle = db.scalar(stmt)
    if battle is not None:
        return battle

    schedule = BATTLE_THEMES[((week_start - BATTLE_EPOCH).days // 7) % len(BATTLE_THEMES)]
    db.add(
        Battle(
            tier=tier,
            theme=schedule["theme"],
            description=schedule[tier],
            week_start=week_start,
            starts_at=clock.kst_day_bounds(week_start)[0],
            ends_at=clock.kst_day_bounds(week_start + dt.timedelta(days=7))[0],
        )
    )
    try:
        db.commit()
    except IntegrityError:  # another request created it first
        db.rollback()
    return db.scalar(stmt)


def ranked_entries(db: Session, battle_id: int) -> Sequence[Entry]:
    """Most votes first; on a tie, whoever submitted first ranks higher."""
    return db.scalars(
        select(Entry)
        .options(joinedload(Entry.user))
        .where(Entry.battle_id == battle_id)
        .order_by(Entry.vote_count.desc(), Entry.created_at.asc(), Entry.id.asc())
    ).all()


def finalize_due_battles(db: Session, now: dt.datetime) -> None:
    """Hand out ranks and rank points for every battle that has ended but isn't finalized yet.

    There is no scheduler: whichever request comes first after a battle ends does it. It is
    idempotent and safe under concurrency (see _finalize).
    """
    for battle_id in db.scalars(select(Battle.id).where(Battle.finalized_at.is_(None), Battle.ends_at <= now)).all():
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
        for rank, entry in enumerate(entries, start=1):
            user = db.get(User, entry.user_id)
            level_from = level_for(user.total_points)
            reward = RANK_POINTS.get(rank, 0)
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


def entry_out(entry: Entry, state: str) -> EntryOut:
    return EntryOut(
        id=entry.id,
        battle_id=entry.battle_id,
        dish_name=entry.dish_name,
        description=entry.description,
        photo_url=image_url(entry.photo_filename),
        author=user_brief(entry.user),
        vote_count=entry.vote_count,
        created_at=entry.created_at,
        state=state,
    )


def entry_outs(
    entries: Sequence[Entry], viewer_id: int, my_vote_entry_id: Optional[int], can_vote: bool
) -> List[EntryOut]:
    return [entry_out(e, entry_state(e, viewer_id, my_vote_entry_id, can_vote)) for e in entries]
