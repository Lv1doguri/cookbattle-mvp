from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ApiError
from ..models import Exchange, ShopItem, User
from ..schemas import ExchangeOut, ShopItemOut, ShopOut
from ..security import get_current_user
from ..services.points import level_for, spend_points

router = APIRouter(prefix="/shop", tags=["shop"])


def _item_out(item: ShopItem, level: int, points: int) -> ShopItemOut:
    if level < item.required_level:
        state, short = "locked", 0  # "Lv.5부터 교환 가능 — 잠김"
    elif points < item.price_points:
        state, short = "insufficient_points", item.price_points - points  # "1,760P 더 필요해요"
    else:
        state, short = "available", 0
    return ShopItemOut(
        id=item.id,
        name=item.name,
        price_points=item.price_points,
        required_level=item.required_level,
        state=state,
        points_short=short,
    )


@router.get("", response_model=ShopOut)
def shop(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    level = level_for(user.total_points)
    # Registration order (커피 → 학식 → 편의점 → 치킨), which is the order the design lists them in.
    items = db.scalars(select(ShopItem).where(ShopItem.active.is_(True)).order_by(ShopItem.id))
    return ShopOut(points=user.points, level=level, items=[_item_out(i, level, user.points) for i in items])


@router.post("/items/{item_id}/exchange", response_model=ExchangeOut, status_code=201)
def exchange(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[교환하기]. 포인트 차감과 교환 내역 저장이 한 트랜잭션이에요. (MVP: 실제 기프티콘 발송 없음)"""
    item = db.get(ShopItem, item_id)
    if item is None or not item.active:
        raise ApiError(404, "item_not_found", "상품을 찾을 수 없습니다")
    if level_for(user.total_points) < item.required_level:
        raise ApiError(403, "level_locked", f"Lv.{item.required_level}부터 교환할 수 있어요")

    if not spend_points(db, user, item.price_points, reason="exchange", ref_type="shop_item", ref_id=item.id):
        db.rollback()
        raise ApiError(400, "insufficient_points", "포인트가 부족해요")
    db.add(Exchange(user_id=user.id, shop_item_id=item.id, name=item.name, points_spent=item.price_points))
    db.commit()
    return ExchangeOut(item_name=item.name, points_spent=item.price_points, points=user.points)
