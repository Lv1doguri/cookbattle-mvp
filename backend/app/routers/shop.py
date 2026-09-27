from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import clock
from ..content import MAX_EXCHANGES_PER_MONTH_PER_USER
from ..database import get_db
from ..errors import ApiError
from ..models import Exchange, ShopItem, User
from ..schemas import ExchangeOut, ShopItemOut, ShopOut
from ..security import get_current_user
from ..services.points import expire_points, level_for, spend_points

router = APIRouter(prefix="/shop", tags=["shop"])


def _month_exchange_count(db: Session, now, **where) -> int:
    start, end = clock.kst_month_bounds(clock.kst_date(now))
    return (
        db.scalar(
            select(func.count())
            .select_from(Exchange)
            .where(Exchange.created_at >= start, Exchange.created_at < end, *[getattr(Exchange, k) == v for k, v in where.items()])
        )
        or 0
    )


def _item_out(db: Session, item: ShopItem, level: int, points: int, now, user_month_count: int) -> ShopItemOut:
    if level < item.required_level:
        state, short = "locked", 0  # "Lv.5부터 교환 가능 — 잠김"
    elif item.monthly_limit is not None and _month_exchange_count(db, now, shop_item_id=item.id) >= item.monthly_limit:
        state, short = "sold_out_this_month", 0  # "이번 달 물량이 다 나갔어요 (다음 달 1일 재입고)"
    elif user_month_count >= MAX_EXCHANGES_PER_MONTH_PER_USER:
        state, short = "monthly_limit_reached", 0  # "한 달에 N번까지 교환할 수 있어요"
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
    now = clock.utcnow()
    expire_points(db, user, now)
    level = level_for(user.total_points)
    user_month_count = _month_exchange_count(db, now, user_id=user.id)
    # Registration order (편의점 → 아메리카노 → 학식 → 치킨), which is the order the design lists them in.
    items = db.scalars(select(ShopItem).where(ShopItem.active.is_(True)).order_by(ShopItem.id))
    return ShopOut(
        points=user.points, level=level,
        items=[_item_out(db, i, level, user.points, now, user_month_count) for i in items],
    )


@router.post("/items/{item_id}/exchange", response_model=ExchangeOut, status_code=201)
def exchange(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[교환하기]. 포인트 차감과 교환 내역 저장이 한 트랜잭션이에요. (MVP: 실제 기프티콘 발송 없음)

    적자 방지 안전장치: 상품별 월 재고 한도(monthly_limit)와 1인당 월 교환 횟수 상한이 있어요."""
    now = clock.utcnow()
    expire_points(db, user, now)
    item = db.get(ShopItem, item_id)
    if item is None or not item.active:
        raise ApiError(404, "item_not_found", "상품을 찾을 수 없습니다")
    if level_for(user.total_points) < item.required_level:
        raise ApiError(403, "level_locked", f"Lv.{item.required_level}부터 교환할 수 있어요")
    if item.monthly_limit is not None and _month_exchange_count(db, now, shop_item_id=item.id) >= item.monthly_limit:
        raise ApiError(400, "sold_out_this_month", "이번 달 물량이 다 나갔어요 (다음 달 1일 재입고)")
    if _month_exchange_count(db, now, user_id=user.id) >= MAX_EXCHANGES_PER_MONTH_PER_USER:
        raise ApiError(400, "monthly_limit_reached", f"한 달에 {MAX_EXCHANGES_PER_MONTH_PER_USER}번까지 교환할 수 있어요")

    if not spend_points(db, user, item.price_points, reason="exchange", ref_type="shop_item", ref_id=item.id):
        db.rollback()
        raise ApiError(400, "insufficient_points", "포인트가 부족해요")
    db.add(Exchange(user_id=user.id, shop_item_id=item.id, name=item.name, points_spent=item.price_points, created_at=now))
    db.commit()
    return ExchangeOut(item_name=item.name, points_spent=item.price_points, points=user.points)
