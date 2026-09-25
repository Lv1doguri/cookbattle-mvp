import datetime as dt
import secrets
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .. import clock
from ..database import get_db
from ..enums import SHOP_CATEGORY_LABEL, ShopCategory
from ..errors import ApiError
from ..models import Coupon, ShopItem, User
from ..schemas import CouponListOut, CouponOut, PurchaseOut, ShopItemOut, ShopOut
from ..security import get_current_user
from ..services.serialize import count
from ..services.xp import spend_coins

router = APIRouter(prefix="/shop", tags=["shop"])
coupons_router = APIRouter(prefix="/me/coupons", tags=["coupons"])

NEW_COUPON_WINDOW = dt.timedelta(hours=24)


def _available(now: dt.datetime):
    return (Coupon.used_at.is_(None), Coupon.expires_at > now)


def _coupon_status(c: Coupon, now: dt.datetime) -> str:
    if c.used_at is not None:
        return "used"
    return "expired" if c.expires_at <= now else "available"


def _coupon_out(c: Coupon, now: dt.datetime) -> CouponOut:
    status = _coupon_status(c, now)
    return CouponOut(
        id=c.id,
        name=c.name,
        value_label=c.value_label,
        value_krw=c.value_krw,
        code=c.code,
        status=status,
        is_new=status == "available" and now - c.created_at < NEW_COUPON_WINDOW,
        created_at=c.created_at,
        expires_at=c.expires_at,
        used_at=c.used_at,
    )


def _item_out(i: ShopItem) -> ShopItemOut:
    return ShopItemOut(
        id=i.id,
        name=i.name,
        category=i.category,
        category_label=SHOP_CATEGORY_LABEL[i.category],
        value_label=i.value_label,
        value_krw=i.value_krw,
        price_coins=i.price_coins,
        validity_days=i.validity_days,
    )


def _new_code(db: Session) -> str:
    for _ in range(10):
        code = "".join(secrets.choice("0123456789") for _ in range(12))
        if db.scalar(select(Coupon.id).where(Coupon.code == code)) is None:
            return code
    raise ApiError(500, "code_generation_failed", "잠시 후 다시 시도해주세요")


# ------------------------------------------------------------------ shop
@router.get("/items", response_model=ShopOut)
def list_items(
    category: Optional[ShopCategory] = Query(None, description="생략하면 전체"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(ShopItem).where(ShopItem.active.is_(True)).order_by(ShopItem.id)
    if category is not None:
        stmt = stmt.where(ShopItem.category == category)
    now = clock.utcnow()
    return ShopOut(
        coins=user.coins,
        available_coupon_count=count(db, Coupon, Coupon.user_id == user.id, *_available(now)),
        items=[_item_out(i) for i in db.scalars(stmt)],
    )


@router.post("/items/{item_id}/purchase", response_model=PurchaseOut, status_code=201)
def purchase(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[구매하기]. 코인 차감과 쿠폰 발급이 한 트랜잭션이라 둘 중 하나만 되는 일은 없어요."""
    item = db.get(ShopItem, item_id)
    if item is None or not item.active:
        raise ApiError(404, "item_not_found", "상품을 찾을 수 없습니다")

    now = clock.utcnow()
    if not spend_coins(db, user, item.price_coins, reason="purchase", ref_type="shop_item", ref_id=item.id):
        db.rollback()
        raise ApiError(400, "insufficient_coins", "코인이 부족해요")

    coupon = Coupon(
        user_id=user.id,
        shop_item_id=item.id,
        name=item.name,
        value_label=item.value_label,
        value_krw=item.value_krw,
        price_paid=item.price_coins,
        code=_new_code(db),
        created_at=now,
        expires_at=now + dt.timedelta(days=item.validity_days),
    )
    db.add(coupon)
    db.commit()
    return PurchaseOut(coupon=_coupon_out(coupon, now), coins=user.coins)


# ------------------------------------------------------------------ my coupons
@coupons_router.get("", response_model=CouponListOut)
def my_coupons(
    status: Literal["available", "used", "expired", "all"] = "available",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = clock.utcnow()
    mine = Coupon.user_id == user.id
    stmt = select(Coupon).where(mine).order_by(Coupon.created_at.desc(), Coupon.id.desc())
    if status == "available":
        stmt = stmt.where(*_available(now))
    elif status == "used":
        stmt = stmt.where(Coupon.used_at.is_not(None))
    elif status == "expired":
        stmt = stmt.where(Coupon.used_at.is_(None), Coupon.expires_at <= now)
    items: List[Coupon] = list(db.scalars(stmt))
    return CouponListOut(
        available_count=count(db, Coupon, mine, *_available(now)),
        used_count=count(db, Coupon, mine, Coupon.used_at.is_not(None)),
        expired_count=count(db, Coupon, mine, Coupon.used_at.is_(None), Coupon.expires_at <= now),
        items=[_coupon_out(c, now) for c in items],
    )


@coupons_router.post("/{coupon_id}/use", response_model=CouponOut)
def use_coupon(coupon_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[쿠폰 사용]. 한 번만 성공하고, 이미 썼거나 기한이 지났으면 실패해요."""
    coupon = db.scalar(select(Coupon).where(Coupon.id == coupon_id, Coupon.user_id == user.id))
    if coupon is None:
        raise ApiError(404, "coupon_not_found", "쿠폰을 찾을 수 없습니다")

    now = clock.utcnow()
    result = db.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id, Coupon.used_at.is_(None), Coupon.expires_at > now)
        .values(used_at=now)
    )
    if result.rowcount != 1:
        db.rollback()
        db.refresh(coupon)
        if coupon.used_at is not None:
            raise ApiError(409, "coupon_already_used", "이미 사용한 쿠폰이에요")
        raise ApiError(410, "coupon_expired", "사용기한이 지난 쿠폰이에요")
    db.commit()
    db.refresh(coupon)
    return _coupon_out(coupon, now)
