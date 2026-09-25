import datetime as dt
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import clock
from ..database import get_db
from ..enums import TIER_LABEL, Category, Tier
from ..errors import ApiError
from ..models import Battle, Ingredient, Post, RecipeRating, User
from ..schemas import IngredientOut, PostPage, RatingIn, RatingOut, RecipeDetailOut, RecipeWinnerOut, StepOut
from ..security import get_current_user
from ..services.serialize import build_post_outs, post_page, post_query

router = APIRouter(prefix="/recipes", tags=["recipes"])

WINNER_LOOKBACK_DAYS = 7


def _rating(db: Session, post_id: int, user_id: int) -> RatingOut:
    avg, n = db.execute(
        select(func.avg(RecipeRating.score), func.count()).where(RecipeRating.post_id == post_id)
    ).one()
    mine = db.scalar(select(RecipeRating.score).where(RecipeRating.post_id == post_id, RecipeRating.user_id == user_id))
    return RatingOut(rating_avg=round(float(avg), 1) if avg is not None else None, rating_count=n, my_rating=mine)


@router.get("", response_model=PostPage)
def list_recipes(
    q: Optional[str] = Query(None, max_length=50, description="요리 이름 또는 재료 이름"),
    category: Optional[Category] = None,
    max_cost: Optional[int] = Query(None, ge=0, description="예: 5000 → '5,000원 이하'"),
    difficulty: Optional[Tier] = None,
    max_minutes: Optional[int] = Query(None, ge=1),
    sort: Literal["latest", "popular"] = "latest",
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = post_query()
    term = (q or "").strip()
    if term:
        stmt = stmt.where(
            or_(
                Post.title.icontains(term, autoescape=True),
                Post.id.in_(select(Ingredient.post_id).where(Ingredient.name.icontains(term, autoescape=True))),
            )
        )
    if category is not None:
        stmt = stmt.where(Post.category == category)
    if max_cost is not None:
        stmt = stmt.where(Post.cost_krw <= max_cost)
    if difficulty is not None:
        stmt = stmt.where(Post.difficulty == difficulty)
    if max_minutes is not None:
        stmt = stmt.where(Post.cook_minutes <= max_minutes)
    if sort == "popular":
        stmt = stmt.order_by((Post.like_count + Post.save_count).desc(), Post.id.desc())
    else:
        stmt = stmt.order_by(Post.id.desc())
    return post_page(db, stmt, user, limit, offset)


@router.get("/winners", response_model=List[RecipeWinnerOut])
def winners(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """'우승 레시피 · 이번 주 대결 1위': 단계별로, 최근 7일 안에 마감된 가장 최근 대결의 1위 게시물."""
    now = clock.utcnow()
    since = clock.kst_date(now) - dt.timedelta(days=WINNER_LOOKBACK_DAYS)
    found = []
    for tier in Tier:
        finished = db.scalars(
            select(Battle)
            .where(Battle.tier == tier, Battle.ends_at <= now, Battle.date >= since)
            .order_by(Battle.date.desc())
        ).all()
        for battle in finished:
            top = db.scalar(
                post_query()
                .where(Post.battle_id == battle.id)
                .order_by(Post.battle_score.desc(), Post.created_at.asc(), Post.id.asc())
                .limit(1)
            )
            if top is not None:
                found.append((tier, battle, top))
                break
    outs = build_post_outs(db, [top for _, _, top in found], user)
    return [
        RecipeWinnerOut(tier=tier, tier_label=TIER_LABEL[tier], battle_date=battle.date, recipe=out)
        for (tier, battle, _), out in zip(found, outs)
    ]


@router.get("/{post_id}", response_model=RecipeDetailOut)
def recipe_detail(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.scalar(
        post_query().where(Post.id == post_id).options(selectinload(Post.ingredients), selectinload(Post.steps))
    )
    if post is None:
        raise ApiError(404, "recipe_not_found", "레시피를 찾을 수 없습니다")
    base = build_post_outs(db, [post], user)[0]
    return RecipeDetailOut(
        **base.model_dump(),
        ingredients=[IngredientOut(name=i.name, amount=i.amount) for i in post.ingredients],
        steps=[StepOut(order=s.position, text=s.text) for s in post.steps],
        **_rating(db, post_id, user.id).model_dump(),
    )


@router.put("/{post_id}/rating", response_model=RatingOut)
def rate_recipe(post_id: int, body: RatingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if post is None:
        raise ApiError(404, "recipe_not_found", "레시피를 찾을 수 없습니다")
    if post.author_id == user.id:
        raise ApiError(400, "cannot_rate_own", "내 레시피에는 평점을 줄 수 없어요")
    existing = db.get(RecipeRating, (user.id, post_id))
    if existing is not None:
        existing.score = body.score
    else:
        db.add(RecipeRating(user_id=user.id, post_id=post_id, score=body.score))
    try:
        db.commit()
    except IntegrityError:  # double tap raced; last write wins
        db.rollback()
        db.get(RecipeRating, (user.id, post_id)).score = body.score
        db.commit()
    return _rating(db, post_id, user.id)
