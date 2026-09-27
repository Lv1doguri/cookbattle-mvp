import math
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import clock
from ..content import FIRST_BATTLE_BONUS, PARTICIPATION_POINTS, PHOTO_TTL, VOTE_POINTS
from ..database import get_db
from ..enums import TIER_LABEL, BattleKind, BattlePhase, Tier
from ..errors import ApiError
from ..models import Battle, Entry, Ingredient, LedgerEntry, Photo, Recipe, RecipeTool, Step, User, Vote
from ..schemas import (
    BattleHomeOut,
    BattleOut,
    EntryListOut,
    JoinIn,
    JoinOut,
    LastResultOut,
    NotifyOut,
    RecipeCreateIn,
    RecipeDetailOut,
    ResultMe,
    ResultOut,
    ResultRow,
    VoteOut,
    VotingCardOut,
)
from ..security import get_current_user
from ..services.accounts import count, user_brief
from ..services.battles import (
    award_streak,
    battle_title,
    can_vote_now,
    entry_out,
    entry_outs,
    find_voting_battle,
    finalize_due_battles,
    get_or_create_daily_battle,
    get_or_create_theme_battle,
    is_open,
    phase,
    ranked_entries,
    week_label,
)
from ..services.points import grant_points
from ..services.recipes import build_detail, recipe_query

router = APIRouter(tags=["battles"])

TOP_N = 10


def _get_battle(db: Session, battle_id: int) -> Battle:
    battle = db.get(Battle, battle_id)
    if battle is None:
        raise ApiError(404, "battle_not_found", "대결을 찾을 수 없습니다")
    return battle


def _my_entry(db: Session, battle_id: int, user_id: int) -> Optional[Entry]:
    return db.scalar(
        select(Entry)
        .options(joinedload(Entry.user), joinedload(Entry.photo))
        .where(Entry.battle_id == battle_id, Entry.user_id == user_id)
    )


def _is_my_group(battle: Battle, user: User) -> bool:
    """테마 대결은 실력 구분 없이 전체 공통이라 항상 '내 그룹'이에요."""
    return battle.kind == BattleKind.theme or battle.tier == user.tier


def _tier_label(battle: Battle) -> Optional[str]:
    return TIER_LABEL[battle.tier] if battle.tier else None


def _last_result_for(db: Session, battle: Battle, user: User) -> Optional[LastResultOut]:
    last = db.scalar(
        select(Battle)
        .where(
            Battle.kind == battle.kind,
            Battle.tier == battle.tier if battle.tier is not None else Battle.tier.is_(None),
            Battle.finalized_at.is_not(None),
            Battle.week_start < battle.week_start,
        )
        .order_by(Battle.week_start.desc())
        .limit(1)
    )
    if last is None:
        return None
    last_entry = _my_entry(db, last.id, user.id)
    return LastResultOut(
        battle_id=last.id,
        title=battle_title(last),
        week_label=week_label(last.week_start),
        status="void" if last.is_void else "ranked",
        joined=last_entry is not None,
        my_rank=last_entry.rank if last_entry else None,
    )


def _battle_out(db: Session, battle: Battle, user: User, now) -> BattleOut:
    mine = _my_entry(db, battle.id, user.id)
    open_ = is_open(battle, now)
    is_my_group = _is_my_group(battle, user)
    ph = phase(battle, now)
    deadline = battle.ends_at if ph == BattlePhase.cooking else battle.voting_ends_at
    seconds_left = max(0, int((deadline - now).total_seconds()))
    return BattleOut(
        id=battle.id,
        kind=battle.kind,
        tier=battle.tier,
        tier_label=_tier_label(battle),
        title=battle_title(battle),
        theme=battle.theme,
        description=battle.description,
        week_label=week_label(battle.week_start),
        starts_at=battle.starts_at,
        ends_at=battle.ends_at,
        voting_ends_at=battle.voting_ends_at,
        phase=ph,
        seconds_left=seconds_left,
        days_left=max(0, math.ceil(max(0, int((battle.ends_at - now).total_seconds())) / 86400)),
        server_time=now,
        participants=count(db, Entry, Entry.battle_id == battle.id),
        is_open=open_,
        is_my_group=is_my_group,
        has_joined=mine is not None,
        can_join=is_my_group and open_ and mine is None,
        my_entry=entry_out(mine, "mine") if mine else None,
        last_result=_last_result_for(db, battle, user),
    )


@router.get("/battles/current", response_model=BattleOut)
def current_battle(
    tier: Optional[Tier] = Query(None, description="대결 그룹 탭. 생략하면 내 그룹 (kind=theme이면 무시돼요)"),
    kind: BattleKind = Query(BattleKind.daily, description="daily=오늘의 대결(그룹별) · theme=테마 대결(전체 공통)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """대결 하나. 카메라/요리인증/참가완료 화면처럼 '내 대결'이 필요하면 파라미터 없이 부르면 돼요
    (kind=daily, tier=내 그룹). 대결 홈 화면은 이 API 대신 `GET /battles/home`을 한 번만 부르세요."""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    battle = (
        get_or_create_theme_battle(db, now)
        if kind == BattleKind.theme
        else get_or_create_daily_battle(db, tier or user.tier, now)
    )
    return _battle_out(db, battle, user, now)


@router.get("/battles/home", response_model=BattleHomeOut)
def battle_home(
    tier: Optional[Tier] = Query(None, description="생략하면 내 그룹"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """대결 홈 화면 한 번에: 오늘의 대결(그룹별) + 테마 대결(전체 공통) + 지난 대회 투표 카드."""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    group = tier or user.tier

    daily = get_or_create_daily_battle(db, group, now)
    theme = get_or_create_theme_battle(db, now)

    voting = find_voting_battle(db, BattleKind.daily, group, now) or find_voting_battle(db, BattleKind.theme, None, now)
    voting_card = None
    if voting is not None:
        my_vote = db.get(Vote, (voting.id, user.id))
        hours_left = max(1, math.ceil((voting.voting_ends_at - now).total_seconds() / 3600))
        voting_card = VotingCardOut(
            battle_id=voting.id,
            kind=voting.kind,
            title=battle_title(voting),
            group_label=_tier_label(voting),
            participants=count(db, Entry, Entry.battle_id == voting.id),
            hours_left=hours_left,
            has_voted=my_vote is not None,
        )

    return BattleHomeOut(
        daily=_battle_out(db, daily, user, now),
        theme=_battle_out(db, theme, user, now),
        voting=voting_card,
    )


@router.get("/battles/{battle_id}/entries", response_model=EntryListOut)
def list_entries(battle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """투표 화면: 출품작 목록. 각 항목의 state로 버튼을 정하세요
    (votable=투표 · mine=투표 불가 · voted=투표함 · vote_done=투표 완료 · unavailable=투표 못 하는 상태).
    투표는 대회 종료 후 24시간 동안만 가능해요(phase=voting)."""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    battle = _get_battle(db, battle_id)

    entries = db.scalars(
        select(Entry)
        .options(joinedload(Entry.user), joinedload(Entry.photo))
        .where(Entry.battle_id == battle_id)
        .order_by(Entry.created_at.asc(), Entry.id.asc())
    ).all()
    my_vote = db.get(Vote, (battle_id, user.id))
    ph = phase(battle, now)
    can_vote = can_vote_now(battle, now) and _is_my_group(battle, user)
    return EntryListOut(
        battle_id=battle.id,
        kind=battle.kind,
        tier=battle.tier,
        tier_label=_tier_label(battle),
        title=battle_title(battle),
        participants=len(entries),
        phase=ph,
        can_vote=can_vote,
        has_voted=my_vote is not None,
        my_vote_entry_id=my_vote.entry_id if my_vote else None,
        items=entry_outs(db, entries, user.id, my_vote.entry_id if my_vote else None, can_vote),
    )


@router.post("/battles/{battle_id}/entries", response_model=JoinOut, status_code=201)
def join_battle(
    battle_id: int,
    body: JoinIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """요리 인증 화면의 [제출]. 먼저 `POST /photos`로 받은 photo_id를 함께 보내요. 참가하면 +1P."""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    battle = _get_battle(db, battle_id)

    if not _is_my_group(battle, user):
        raise ApiError(403, "wrong_group", f"내 그룹({TIER_LABEL[user.tier]}) 대결에만 참가할 수 있어요")
    if not is_open(battle, now):
        raise ApiError(400, "battle_closed", "마감된 대결이에요")
    if _my_entry(db, battle.id, user.id) is not None:
        raise ApiError(409, "already_entered", "한 대결에는 한 번만 참가할 수 있어요")

    photo = db.get(Photo, body.photo_id)
    if photo is None or photo.user_id != user.id:
        raise ApiError(404, "photo_not_found", "촬영한 사진을 찾을 수 없어요. 다시 촬영해주세요")
    if db.scalar(select(Entry.id).where(Entry.photo_id == photo.id)) is not None:
        raise ApiError(409, "photo_already_used", "이미 제출한 사진이에요. 다시 촬영해주세요")
    if now > photo.captured_at + PHOTO_TTL:
        raise ApiError(400, "photo_expired", "촬영한 지 너무 오래됐어요. 다시 촬영해주세요")

    entry = Entry(
        battle_id=battle.id,
        user_id=user.id,
        photo_id=photo.id,
        dish_name=body.dish_name,
        description=body.description,
        created_at=now,
    )
    db.add(entry)
    try:
        db.flush()
    except IntegrityError:  # double tap: the other request already entered / used this photo
        db.rollback()
        raise ApiError(409, "already_entered", "한 대결에는 한 번만 참가할 수 있어요")

    grant_points(db, user, PARTICIPATION_POINTS, reason="participation", ref_type="entry", ref_id=entry.id)
    awarded = PARTICIPATION_POINTS
    is_first_ever = db.scalar(select(LedgerEntry.id).where(LedgerEntry.user_id == user.id, LedgerEntry.reason == "first_battle")) is None
    if is_first_ever:
        grant_points(db, user, FIRST_BATTLE_BONUS, reason="first_battle", ref_type="user", ref_id=user.id)
        awarded += FIRST_BATTLE_BONUS
    award_streak(db, user, battle)
    db.commit()
    return JoinOut(entry=entry_out(entry, "mine"), points_awarded=awarded, points=user.points)


@router.post("/entries/{entry_id}/notify", response_model=NotifyOut)
def toggle_notify(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """참가 완료 화면의 [대회 종료 시 알림 받기]. MVP: 실제 알림 발송은 없고 원하는지만 저장돼요."""
    entry = db.get(Entry, entry_id)
    if entry is None:
        raise ApiError(404, "entry_not_found", "출품작을 찾을 수 없습니다")
    if entry.user_id != user.id:
        raise ApiError(403, "not_your_entry", "내 출품작이 아니에요")
    entry.notify_on_close = not entry.notify_on_close
    db.commit()
    return NotifyOut(notify_on_close=entry.notify_on_close)


@router.post("/entries/{entry_id}/vote", response_model=VoteOut)
def vote(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[투표]. 대회 종료 후 24시간 동안만, 대결 하나에 1인 1표, 자기 작품 불가. 투표하면 +1P."""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    entry = db.get(Entry, entry_id)
    if entry is None:
        raise ApiError(404, "entry_not_found", "출품작을 찾을 수 없습니다")
    battle = _get_battle(db, entry.battle_id)

    if not _is_my_group(battle, user):
        raise ApiError(403, "wrong_group", "내 그룹의 대결에만 투표할 수 있어요")
    if entry.user_id == user.id:
        raise ApiError(400, "own_entry", "자기 작품에는 투표할 수 없어요")
    if phase(battle, now) == BattlePhase.cooking:
        raise ApiError(400, "voting_not_started", "투표는 대회가 끝난 뒤부터 할 수 있어요")
    if phase(battle, now) == BattlePhase.closed:
        raise ApiError(400, "voting_closed", "투표가 마감됐어요")

    db.add(Vote(battle_id=battle.id, voter_id=user.id, entry_id=entry.id, created_at=now))
    try:
        db.flush()
    except IntegrityError:  # primary key (battle_id, voter_id): already voted in this battle
        db.rollback()
        raise ApiError(409, "already_voted", "이미 투표하셨습니다")
    db.execute(update(Entry).where(Entry.id == entry.id).values(vote_count=Entry.vote_count + 1))
    grant_points(db, user, VOTE_POINTS, reason="vote", ref_type="entry", ref_id=entry.id)
    db.commit()
    db.refresh(entry)
    return VoteOut(entry_id=entry.id, vote_count=entry.vote_count, has_voted=True, points_awarded=VOTE_POINTS)


@router.get("/battles/{battle_id}/result", response_model=ResultOut)
def battle_result(battle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """대결 결과. 투표 기간이 끝나기 전이면 409(battle_not_finished). 참가자 3명 미만이면 status=void(순위 없음)."""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    battle = _get_battle(db, battle_id)
    if battle.finalized_at is None:
        raise ApiError(409, "battle_not_finished", "아직 투표가 끝나지 않은 대결이에요")

    entries = ranked_entries(db, battle.id)
    void = battle.is_void
    # entry_id -> id of the recipe its author already shared from it
    shared = {}
    if entries:
        rows_ = db.execute(select(Recipe.entry_id, Recipe.id).where(Recipe.entry_id.in_([e.id for e in entries])))
        shared = {entry_id: recipe_id for entry_id, recipe_id in rows_}

    rows: List[ResultRow] = []
    if not void:
        for i, e in enumerate(entries):
            same_as_prev = i > 0 and entries[i - 1].vote_count == e.vote_count
            same_as_next = i + 1 < len(entries) and entries[i + 1].vote_count == e.vote_count
            rows.append(
                ResultRow(
                    rank=e.rank,
                    entry_id=e.id,
                    user=user_brief(e.user),
                    dish_name=e.dish_name,
                    vote_count=e.vote_count,
                    submitted_at=e.created_at,
                    tie="tied" if same_as_prev else ("first" if same_as_next else None),
                    is_me=e.user_id == user.id,
                    is_winner=e.rank == 1,
                    can_share_recipe=e.user_id == user.id and e.rank == 1 and e.id not in shared,
                )
            )

    mine = next((e for e in entries if e.user_id == user.id), None)
    me = ResultMe(
        joined=mine is not None,
        rank=mine.rank if mine else None,
        participation_points=PARTICIPATION_POINTS if mine else 0,
        rank_points=mine.rank_points if mine else 0,
        level_from=mine.level_from if mine else None,
        level_to=mine.level_to if mine else None,
        leveled_up=bool(mine and mine.level_from and mine.level_to and mine.level_to > mine.level_from),
        can_share_recipe=bool(mine and not void and mine.rank == 1 and mine.id not in shared),
        shared_recipe_id=shared.get(mine.id) if mine else None,
    )
    return ResultOut(
        battle_id=battle.id,
        kind=battle.kind,
        tier=battle.tier,
        tier_label=_tier_label(battle),
        title=battle_title(battle),
        theme=battle.theme,
        week_label=week_label(battle.week_start),
        participants=len(entries),
        status="void" if void else "ranked",
        podium=rows[:3],
        top10=rows[:TOP_N],
        me=me,
    )


@router.post("/entries/{entry_id}/recipe", response_model=RecipeDetailOut, status_code=201)
def share_recipe(
    entry_id: int,
    body: RecipeCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """1등이 자기 레시피를 레시피 탭에 공유. (디자인에 입력 화면이 없어서 필드는 레시피 상세 기준으로 잡았어요)"""
    now = clock.utcnow()
    finalize_due_battles(db, now)
    entry = db.scalar(select(Entry).options(joinedload(Entry.battle), joinedload(Entry.photo)).where(Entry.id == entry_id))
    if entry is None:
        raise ApiError(404, "entry_not_found", "출품작을 찾을 수 없습니다")
    if entry.user_id != user.id:
        raise ApiError(403, "not_your_entry", "내 출품작이 아니에요")
    battle = entry.battle
    if battle.finalized_at is None or battle.is_void or entry.rank != 1:
        raise ApiError(403, "not_winner", "대결 1등만 레시피를 공유할 수 있어요")
    if db.scalar(select(Recipe.id).where(Recipe.entry_id == entry.id)) is not None:
        raise ApiError(409, "already_shared", "이미 레시피를 공유했어요")

    recipe = Recipe(
        author_id=user.id,
        entry_id=entry.id,
        title=body.name or entry.dish_name,
        category=body.category,
        cost_krw=body.price,
        cook_minutes=body.minutes,
        difficulty=body.difficulty,
        win_label=f"{battle_title(battle)} 1등",
        photo_filename=entry.photo.filename,
        created_at=now,
    )
    recipe.ingredients = [Ingredient(position=i, name=x.name, amount=x.amount) for i, x in enumerate(body.ingredients)]
    recipe.steps = [Step(position=i + 1, text=s.text) for i, s in enumerate(body.steps)]
    recipe.tools = [RecipeTool(tool=t) for t in dict.fromkeys(body.tools)]
    db.add(recipe)
    try:
        db.commit()
    except IntegrityError:  # shared twice at once
        db.rollback()
        raise ApiError(409, "already_shared", "이미 레시피를 공유했어요")

    fresh = db.scalar(
        recipe_query()
        .where(Recipe.id == recipe.id)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps), selectinload(Recipe.tools))
    )
    return build_detail(db, fresh, user)
