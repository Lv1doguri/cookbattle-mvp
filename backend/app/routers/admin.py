"""관리자 전용: 대결 시작/마감(데모용), 카테고리·상품 등록, 작품 숨김, 교환 내역."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_admin_user
from ..database import get_db
from ..models import Category, Exchange, ShopItem, Submission, User
from ..schemas import BattleOut, CategoryCreate, CategoryOut, PhaseChange, ShopItemCreate, StartBattleRequest
from ..services.battle import (
    active_battle, close_battle, close_expired_battles, get_battle_or_404, set_phase, start_battle,
)
from ..services.ai_vision import is_enabled
from ..services.serializers import battle_out
from ..config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/battles/{battle_id}/close", response_model=BattleOut)
def close_now(battle_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    """데모용 수동 종료 → 순위 포인트 지급. 다음에 /battles/current를 부르면 새 대결이 열린다."""
    battle = get_battle_or_404(db, battle_id)
    if battle.is_closed:
        raise HTTPException(status_code=400, detail="이미 끝난 대결입니다")
    close_battle(db, battle)
    db.refresh(battle)
    return battle_out(battle, db, admin)


@router.post("/battles/start", response_model=BattleOut)
def start_now(payload: StartBattleRequest, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    """그룹의 새 대결 시작 (category_id 없으면 랜덤). group: low/mid/high 또는 fail(망한 요리 대회).
    진행 중 대결이 있으면 먼저 종료해야 함."""
    groups = list(rules.LEAGUE_GROUPS) + [rules.FAIL_GROUP]
    if payload.group not in groups:
        raise HTTPException(status_code=400, detail=f"group은 {groups} 중 하나")
    close_expired_battles(db)
    if active_battle(db, payload.group):
        raise HTTPException(status_code=400, detail="이 그룹에 진행 중인 대결이 있어요. 먼저 종료하세요")
    return battle_out(start_battle(db, payload.group, payload.category_id), db, admin)


@router.post("/battles/{battle_id}/phase", response_model=BattleOut)
def change_phase(battle_id: int, payload: PhaseChange, db: Session = Depends(get_db),
                 admin: User = Depends(get_admin_user)):
    """[시연용] 날짜를 기다리지 않고 바로 요리 기간(cooking) 또는 투표 기간(voting)으로 전환."""
    battle = get_battle_or_404(db, battle_id)
    if battle.is_closed:
        raise HTTPException(status_code=400, detail="이미 끝난 대결입니다")
    set_phase(db, battle, payload.phase)
    db.refresh(battle)
    return battle_out(battle, db, admin)


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    return [CategoryOut(id=c.id, name=c.name, description=c.description or "")
            for c in db.query(Category).order_by(Category.id).all()]


@router.post("/categories", response_model=CategoryOut)
def add_category(payload: CategoryCreate, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    c = Category(name=payload.name, description=payload.description, kind=payload.kind)
    db.add(c)
    db.commit()
    db.refresh(c)
    return CategoryOut(id=c.id, name=c.name, description=c.description or "")


@router.post("/shop/items")
def add_shop_item(payload: ShopItemCreate, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    item = ShopItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "price": item.price, "min_level": item.min_level, "stock": item.stock}


@router.get("/exchanges")
def all_exchanges(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    rows = db.query(Exchange).order_by(Exchange.created_at.desc()).limit(200).all()
    return [{"id": e.id, "nickname": e.user.nickname, "item_name": e.item.name, "price": e.price,
             "created_at": e.created_at} for e in rows]


@router.post("/submissions/{submission_id}/hide")
def set_hidden(submission_id: int, hidden: bool = True, db: Session = Depends(get_db),
               _admin: User = Depends(get_admin_user)):
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail="작품을 찾을 수 없습니다")
    s.is_hidden = hidden
    db.commit()
    return {"submission_id": s.id, "is_hidden": s.is_hidden}


@router.get("/ai/status")
def ai_status(_admin: User = Depends(get_admin_user)):
    """이미지 인식 AI 설정 확인 (키 값은 노출하지 않음)."""
    return {
        "enabled": is_enabled(),
        "mode": settings.ai_check_mode,
        "model": settings.anthropic_model,
        "api_key_set": bool(settings.anthropic_api_key.strip()),
    }
