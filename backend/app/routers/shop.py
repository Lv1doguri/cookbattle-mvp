"""상점: 보유 포인트로 기프티콘 교환.

적자 방지 안전장치 (기획: 수익화·포인트 설계):
- 상품별 월 교환 한도(monthly_limit) — 달마다 자동 초기화, 나가는 돈의 상한을 고정
- 상품별 전체 누적 재고(stock) — 그대로 유지
- 1인당 월 교환 횟수 상한(MAX_EXCHANGES_PER_MONTH_PER_USER)
- 보유 포인트는 POINT_EXPIRY_DAYS 지나면 소멸 (조회·교환 시점에 lazy하게 정리)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Exchange, ShopItem, User
from ..schemas import ExchangeOut, ShopItemOut
from ..services.points import expire_points
from ..timeutil import month_start_utc

router = APIRouter(prefix="/shop", tags=["shop"])


def _month_exchange_count(db: Session, **filters) -> int:
    return db.query(Exchange).filter(Exchange.created_at >= month_start_utc()).filter_by(**filters).count()


def _blocked_reason(db: Session, item: ShopItem, user: User, user_month_count: int) -> Optional[str]:
    if item.stock is not None and item.stock <= 0:
        return "품절"
    if item.monthly_limit is not None and _month_exchange_count(db, item_id=item.id) >= item.monthly_limit:
        return "이번 달 물량이 다 나갔어요 (다음 달 1일 재입고)"
    if user.level < item.min_level:
        return f"{item.min_level}레벨부터 교환 가능"
    if user_month_count >= rules.MAX_EXCHANGES_PER_MONTH_PER_USER:
        return f"한 달에 {rules.MAX_EXCHANGES_PER_MONTH_PER_USER}번까지 교환할 수 있어요"
    if (user.points or 0) < item.price:
        return f"{item.price - (user.points or 0)}포인트 더 필요해요"
    return None


def _out(db: Session, item: ShopItem, user: User, user_month_count: int) -> ShopItemOut:
    reason = _blocked_reason(db, item, user, user_month_count)
    return ShopItemOut(
        id=item.id, name=item.name, description=item.description or "", price=item.price,
        min_level=item.min_level, stock=item.stock, can_exchange=reason is None, blocked_reason=reason,
    )


@router.get("/items", response_model=list[ShopItemOut])
def list_items(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if expire_points(db, user):
        db.commit()
        db.refresh(user)
    items = db.query(ShopItem).filter(ShopItem.is_active.is_(True)).order_by(ShopItem.price, ShopItem.id).all()
    user_month_count = _month_exchange_count(db, user_id=user.id)
    return [_out(db, i, user, user_month_count) for i in items]


@router.post("/items/{item_id}/exchange", response_model=ExchangeOut)
def exchange(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if expire_points(db, user):
        db.commit()
        db.refresh(user)
    item = db.query(ShopItem).filter(ShopItem.id == item_id, ShopItem.is_active.is_(True)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
    user_month_count = _month_exchange_count(db, user_id=user.id)
    reason = _blocked_reason(db, item, user, user_month_count)
    if reason:
        raise HTTPException(status_code=400, detail=reason)

    # 조건부 UPDATE로 차감 → 동시에 두 번 눌러도 포인트가 모자라면 두 번째는 실패 (이중 사용 방지)
    price = item.price
    ok = (
        db.query(User)
        .filter(User.id == user.id, User.points >= price)
        .update({User.points: User.points - price}, synchronize_session=False)
    )
    if not ok:
        db.rollback()
        raise HTTPException(status_code=400, detail="포인트가 부족해요")
    if item.stock is not None:
        ok = (
            db.query(ShopItem)
            .filter(ShopItem.id == item.id, ShopItem.stock > 0)
            .update({ShopItem.stock: ShopItem.stock - 1}, synchronize_session=False)
        )
        if not ok:
            db.rollback()
            raise HTTPException(status_code=400, detail="품절")
    ex = Exchange(user_id=user.id, item_id=item.id, price=price)
    db.add(ex)
    db.commit()
    db.refresh(ex)
    db.refresh(user)
    return ExchangeOut(id=ex.id, item_id=item.id, item_name=item.name, price=ex.price,
                       created_at=ex.created_at, points_left=user.points)
