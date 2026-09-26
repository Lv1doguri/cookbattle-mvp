"""상점: 보유 포인트로 기프티콘 교환 (MVP: 차감 + 교환 내역 기록까지만)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Exchange, ShopItem, User
from ..schemas import ExchangeOut, ShopItemOut

router = APIRouter(prefix="/shop", tags=["shop"])


def _blocked_reason(item: ShopItem, user: User) -> Optional[str]:
    if item.stock is not None and item.stock <= 0:
        return "품절"
    if user.level < item.min_level:
        return f"{item.min_level}레벨부터 교환 가능"
    if (user.points or 0) < item.price:
        return f"{item.price - (user.points or 0)}포인트 더 필요해요"
    return None


def _out(item: ShopItem, user: User) -> ShopItemOut:
    reason = _blocked_reason(item, user)
    return ShopItemOut(
        id=item.id, name=item.name, description=item.description or "", price=item.price,
        min_level=item.min_level, stock=item.stock, can_exchange=reason is None, blocked_reason=reason,
    )


@router.get("/items", response_model=list[ShopItemOut])
def list_items(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(ShopItem).filter(ShopItem.is_active.is_(True)).order_by(ShopItem.price, ShopItem.id).all()
    return [_out(i, user) for i in items]


@router.post("/items/{item_id}/exchange", response_model=ExchangeOut)
def exchange(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(ShopItem).filter(ShopItem.id == item_id, ShopItem.is_active.is_(True)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
    reason = _blocked_reason(item, user)
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
