from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import clock
from ..content import SAVING_PER_COOKING_KRW
from ..database import get_db
from ..enums import TIER_LABEL
from ..errors import ApiError
from ..models import Entry, Recipe, RecipeSave, RecipeView, Review, User
from ..schemas import HistoryItem, HomeOut, MeOut, MyReviewOut, ProfileUpdateIn, RecipePage
from ..security import get_current_user, hash_password
from ..services.accounts import build_me, count, next_daily_battle_start, nickname_taken
from ..services.battles import battle_title, finalize_due_battles, period_label
from ..services.images import delete_image, read_image, write_image
from ..services.recipes import build_cards, recipe_page, recipe_query

router = APIRouter(prefix="/me", tags=["me"])

HOME_HISTORY_LIMIT = 20
HOME_REVIEW_LIMIT = 20
RECENT_LIMIT = 20


@router.get("", response_model=MeOut)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_me(db, user)


@router.patch("", response_model=MeOut)
def update_me(body: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """정보 수정 > [저장]. 실력(tier)을 바꾸면 '다음 대결부터' 적용돼요(응답의 pending_tier)."""
    if body.nickname is not None and body.nickname != user.nickname:
        if nickname_taken(db, body.nickname, exclude_user_id=user.id):
            raise ApiError(409, "nickname_taken", "이미 등록된 아이디입니다")
        user.nickname = body.nickname
    if body.email is not None:
        email = body.email.strip().lower()
        if email != user.email:
            if db.scalar(select(User.id).where(User.email == email, User.id != user.id)) is not None:
                raise ApiError(409, "email_taken", "이미 가입된 이메일입니다")
            user.email = email
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.tier is not None:
        if body.tier == user.tier:
            user.next_tier = None
            user.next_tier_at = None
        else:
            user.next_tier = body.tier
            user.next_tier_at = next_daily_battle_start(clock.utcnow())
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "conflict", "이미 사용 중인 닉네임 또는 이메일입니다")
    return build_me(db, user)


@router.put("/avatar", response_model=MeOut)
def set_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """정보 수정 > [사진 변경]. multipart, 필드명 `file`."""
    data, ext = read_image(file)
    old = user.avatar_filename
    user.avatar_filename = write_image(data, ext)
    db.commit()
    delete_image(old)
    return build_me(db, user)


@router.get("/home", response_model=HomeOut)
def home(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """홈 화면 한 번에: 프로필, 이번 달 요리 횟수, 절약한 식비, 참가 이력, 내가 쓴 후기."""
    now = clock.utcnow()
    finalize_due_battles(db, now)

    month_start, month_end = clock.kst_month_bounds(clock.kst_date(now))
    cooking = count(db, Entry, Entry.user_id == user.id, Entry.created_at >= month_start, Entry.created_at < month_end)

    entries = db.scalars(
        select(Entry)
        .options(joinedload(Entry.battle))
        .where(Entry.user_id == user.id)
        .order_by(Entry.created_at.desc(), Entry.id.desc())
        .limit(HOME_HISTORY_LIMIT)
    ).all()
    history = [
        HistoryItem(
            battle_id=e.battle_id,
            entry_id=e.id,
            title=battle_title(e.battle),
            theme=e.battle.theme,
            week_label=period_label(e.battle),
            tier=e.battle.tier,
            tier_label=TIER_LABEL[e.battle.tier] if e.battle.tier else None,
            status="void" if e.battle.is_void else ("ranked" if e.rank is not None else "in_progress"),
            rank=e.rank,
        )
        for e in entries
    ]

    reviews = db.scalars(
        select(Review)
        .options(joinedload(Review.recipe))
        .where(Review.author_id == user.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(HOME_REVIEW_LIMIT)
    ).all()
    return HomeOut(
        me=build_me(db, user),
        cooking_count_this_month=cooking,
        saved_amount_krw=cooking * SAVING_PER_COOKING_KRW,
        history=history,
        reviews=[
            MyReviewOut(id=r.id, recipe_id=r.recipe_id, recipe_name=r.recipe.title, text=r.text, created_at=r.created_at)
            for r in reviews
        ],
        review_total=count(db, Review, Review.author_id == user.id),
    )


@router.get("/saved-recipes", response_model=RecipePage)
def saved_recipes(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """메뉴 > 저장한 레시피."""
    stmt = (
        recipe_query()
        .join(RecipeSave, RecipeSave.recipe_id == Recipe.id)
        .where(RecipeSave.user_id == user.id)
        .order_by(RecipeSave.created_at.desc(), Recipe.id.desc())
    )
    total = count(db, RecipeSave, RecipeSave.user_id == user.id)
    return recipe_page(db, stmt, user, limit, offset, total)


@router.get("/recent-recipes", response_model=RecipePage)
def recent_recipes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """메뉴 > 최근 본 레시피 (최근 20개)."""
    rows = db.scalars(
        recipe_query()
        .join(RecipeView, RecipeView.recipe_id == Recipe.id)
        .where(RecipeView.user_id == user.id)
        .order_by(RecipeView.viewed_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    return RecipePage(total=len(rows), items=build_cards(db, rows, user), has_more=False)


@router.get("/reviews", response_model=List[MyReviewOut])
def my_reviews(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """메뉴 > 내가 쓴 후기."""
    rows = db.scalars(
        select(Review)
        .options(joinedload(Review.recipe))
        .where(Review.author_id == user.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        MyReviewOut(id=r.id, recipe_id=r.recipe_id, recipe_name=r.recipe.title, text=r.text, created_at=r.created_at)
        for r in rows
    ]
