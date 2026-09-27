"""Admin-only demo/ops tools: force a battle's phase or close it immediately (no waiting on real
calendar time), and manage shop items. Everything else in the app runs on its own without these —
they exist purely so a demo/pitch doesn't have to wait days for a battle to naturally finish."""
import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import clock
from ..content import VOTING_WINDOW
from ..database import get_db
from ..errors import ApiError
from ..models import Battle, Entry, ShopItem, User
from ..schemas import AdminBattleOut, AdminCloseOut, AdminPhaseIn, AdminShopItemCreateIn, ShopItemOut
from ..security import get_admin_user
from ..services.accounts import count
from ..services.battles import finalize_due_battles, phase

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_battle(db: Session, battle_id: int) -> Battle:
    battle = db.get(Battle, battle_id)
    if battle is None:
        raise ApiError(404, "battle_not_found", "대결을 찾을 수 없습니다")
    return battle


def _admin_out(battle: Battle, now: dt.datetime) -> AdminBattleOut:
    return AdminBattleOut(
        id=battle.id, kind=battle.kind, phase=phase(battle, now), ends_at=battle.ends_at,
        voting_ends_at=battle.voting_ends_at, finalized_at=battle.finalized_at, is_void=battle.is_void,
    )


@router.post("/battles/{battle_id}/phase", response_model=AdminBattleOut)
def set_phase(
    battle_id: int, body: AdminPhaseIn, _admin: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """날짜를 기다리지 않고 바로 요리 기간(cooking) 또는 투표 기간(voting)으로 전환. 시연용."""
    now = clock.utcnow()
    battle = _get_battle(db, battle_id)
    if battle.finalized_at is not None:
        raise ApiError(400, "battle_already_finalized", "이미 종료된 대결이에요")
    if body.phase == "voting":
        battle.ends_at = now
        if battle.voting_ends_at <= now:
            battle.voting_ends_at = now + VOTING_WINDOW
    else:
        battle.ends_at = now + dt.timedelta(days=1)
        battle.voting_ends_at = battle.ends_at + VOTING_WINDOW
    db.commit()
    db.refresh(battle)
    return _admin_out(battle, now)


@router.post("/battles/{battle_id}/close", response_model=AdminCloseOut)
def close_now(battle_id: int, _admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """투표 기간까지 통째로 건너뛰고 즉시 집계. GET /battles/{id}/result로 결과를 바로 볼 수 있어요."""
    now = clock.utcnow()
    battle = _get_battle(db, battle_id)
    if battle.finalized_at is not None:
        raise ApiError(400, "battle_already_finalized", "이미 종료된 대결이에요")
    battle.ends_at = min(battle.ends_at, now)
    battle.voting_ends_at = now
    db.commit()
    finalize_due_battles(db, now)
    db.refresh(battle)
    participants = count(db, Entry, Entry.battle_id == battle.id)
    return AdminCloseOut(battle_id=battle.id, finalized=True, is_void=battle.is_void, participants=participants)


@router.get("/shop/items", response_model=list[ShopItemOut])
def list_items(_admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    items = db.scalars(select(ShopItem).order_by(ShopItem.id)).all()
    return [
        ShopItemOut(id=i.id, name=i.name, price_points=i.price_points, required_level=i.required_level,
                   state="available", points_short=0)
        for i in items
    ]


@router.post("/shop/items", status_code=201)
def add_item(body: AdminShopItemCreateIn, _admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    item = ShopItem(
        name=body.name, price_points=body.price_points, required_level=body.required_level,
        monthly_limit=body.monthly_limit,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "price_points": item.price_points,
            "required_level": item.required_level, "monthly_limit": item.monthly_limit}


@router.post("/shop/items/{item_id}/deactivate")
def deactivate_item(item_id: int, _admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    item = db.get(ShopItem, item_id)
    if item is None:
        raise ApiError(404, "item_not_found", "상품을 찾을 수 없습니다")
    item.active = False
    db.commit()
    return {"id": item.id, "active": item.active}
