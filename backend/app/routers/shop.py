import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import clock
from ..content import PER_USER_MONTHLY_EXCHANGES
from ..database import get_db
from ..errors import ApiError
from ..models import Exchange, ShopItem, User
from ..schemas import ExchangeOut, ShopItemOut, ShopOut
from ..security import get_current_user
from ..services.images import image_url
from ..services.points import level_for, spend_points

router = APIRouter(prefix="/shop", tags=["shop"])


def _month_start(now: dt.datetime) -> dt.datetime:
    return clock.kst_month_bounds(clock.kst_date(now))[0]


def _item_exchanges_this_month(db: Session, item_id: int, month_start: dt.datetime) -> int:
    return db.scalar(
        select(func.count()).select_from(Exchange)
        .where(Exchange.shop_item_id == item_id, Exchange.created_at >= month_start)
    ) or 0


def _user_exchanges_this_month(db: Session, user_id: int, month_start: dt.datetime) -> int:
    return db.scalar(
        select(func.count()).select_from(Exchange)
        .where(Exchange.user_id == user_id, Exchange.created_at >= month_start)
    ) or 0


def _item_out(item: ShopItem, level: int, points: int, exchanged_this_month: int) -> ShopItemOut:
    if level < item.required_level:
        state, short = "locked", 0  # "Lv.5부터 교환 가능 — 잠김"
    elif item.monthly_limit is not None and exchanged_this_month >= item.monthly_limit:
        state, short = "sold_out", 0  # "이번 달 재고 소진 — 다음 달에 다시"
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
        photo_url=image_url(item.photo_filename),
    )


@router.get("", response_model=ShopOut)
def shop(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    month_start = _month_start(clock.utcnow())
    level = level_for(user.total_points)
    # Registration order (커피 → 학식 → 편의점 → 치킨), which is the order the design lists them in.
    items = db.scalars(select(ShopItem).where(ShopItem.active.is_(True)).order_by(ShopItem.id))
    return ShopOut(
        points=user.points, level=level,
        items=[_item_out(i, level, user.points, _item_exchanges_this_month(db, i.id, month_start)) for i in items],
    )


@router.post("/items/{item_id}/exchange", response_model=ExchangeOut, status_code=201)
def exchange(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[교환하기]. 포인트 차감과 교환 내역 저장이 한 트랜잭션이에요. (MVP: 실제 기프티콘 발송 없음)
    예산 안에서 발송하려고 이번 달 상품별 재고 한도와 1인당 월 교환 횟수 한도를 둬요."""
    month_start = _month_start(clock.utcnow())
    item = db.get(ShopItem, item_id)
    if item is None or not item.active:
        raise ApiError(404, "item_not_found", "상품을 찾을 수 없습니다")
    if level_for(user.total_points) < item.required_level:
        raise ApiError(403, "level_locked", f"Lv.{item.required_level}부터 교환할 수 있어요")
    if item.monthly_limit is not None and _item_exchanges_this_month(db, item.id, month_start) >= item.monthly_limit:
        raise ApiError(409, "item_sold_out", "이번 달 재고가 모두 소진됐어요. 다음 달에 다시 시도해주세요")
    if _user_exchanges_this_month(db, user.id, month_start) >= PER_USER_MONTHLY_EXCHANGES:
        raise ApiError(409, "monthly_limit_reached", f"이번 달 교환 가능 횟수({PER_USER_MONTHLY_EXCHANGES}회)를 다 썼어요")

    if not spend_points(db, user, item.price_points, reason="exchange", ref_type="shop_item", ref_id=item.id):
        db.rollback()
        raise ApiError(400, "insufficient_points", "포인트가 부족해요")
    db.add(Exchange(user_id=user.id, shop_item_id=item.id, name=item.name, points_spent=item.price_points))
    db.commit()
    return ExchangeOut(item_name=item.name, points_spent=item.price_points, points=user.points)
