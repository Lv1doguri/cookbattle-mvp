from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import clock
from ..database import get_db
from ..enums import Budget, Category, CookTime, Tier, Tool
from ..errors import ApiError
from ..models import Recipe, RecipeSave, RecipeView, Review, User
from ..schemas import RecipeDetailOut, RecipePage, ReviewCreateIn, ReviewOut, ReviewPage, SaveOut
from ..security import get_current_user
from ..services.accounts import count, user_brief
from ..services.recipes import apply_filters, build_detail, recipe_page, recipe_query

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _get_recipe(db: Session, recipe_id: int) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise ApiError(404, "recipe_not_found", "레시피를 찾을 수 없습니다")
    return recipe


@router.get("", response_model=RecipePage)
def list_recipes(
    q: Optional[str] = Query(None, max_length=50, description="재료, 요리 이름, 키워드"),
    category: Optional[List[Category]] = Query(None, description="여러 개 선택 가능 (OR)"),
    budget: Optional[List[Budget]] = Query(None, description="under_5000 · 5000_to_10000 · over_10000"),
    time: Optional[List[CookTime]] = Query(None, description="le_10 · le_15 · le_30 · ge_60"),
    difficulty: Optional[List[Tier]] = Query(None),
    tool: Optional[List[Tool]] = Query(None),
    essential: Optional[bool] = Query(None, description="true = '자취 필수' 칩"),
    sort: Literal["latest", "popular"] = Query("latest", description="popular = 저장 수 많은 순"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """레시피 목록/검색/필터. 그룹이 다르면 AND, 같은 그룹 안에서 여러 개면 OR.

    필터 화면의 "레시피 N개 보기"는 같은 파라미터에 limit=1로 부르고 응답의 `total`을 쓰세요.
    빠른 필터 칩: 5천원 이하=budget=under_5000 · 15분 이내=time=le_15 · 초급=difficulty=beginner ·
    자취 필수=essential=true.
    """
    filters = dict(
        q=q, categories=category, budgets=budget, times=time, difficulties=difficulty, tools=tool, essential=essential
    )
    total = db.scalar(select(func.count()).select_from(apply_filters(select(Recipe.id), **filters).subquery())) or 0
    stmt = apply_filters(recipe_query(), **filters)
    if sort == "popular":
        stmt = stmt.order_by(Recipe.save_count.desc(), Recipe.id.desc())
    else:
        stmt = stmt.order_by(Recipe.created_at.desc(), Recipe.id.desc())
    return recipe_page(db, stmt, user, limit, offset, total)


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def recipe_detail(recipe_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.scalar(
        recipe_query()
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps), selectinload(Recipe.tools))
    )
    if recipe is None:
        raise ApiError(404, "recipe_not_found", "레시피를 찾을 수 없습니다")

    view = db.get(RecipeView, (user.id, recipe_id))
    if view is not None:
        view.viewed_at = clock.utcnow()
    else:
        db.add(RecipeView(user_id=user.id, recipe_id=recipe_id, viewed_at=clock.utcnow()))
    try:
        db.commit()
    except IntegrityError:  # two tabs opened it at once; the view is recorded either way
        db.rollback()

    return build_detail(db, recipe, user)


@router.post("/{recipe_id}/save", response_model=SaveOut)
def save_recipe(recipe_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """북마크 켜기. 이미 저장했다면 그대로 성공(연타 안전)."""
    recipe = _get_recipe(db, recipe_id)
    if db.get(RecipeSave, (user.id, recipe_id)) is None:
        db.add(RecipeSave(user_id=user.id, recipe_id=recipe_id))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
        else:
            db.execute(update(Recipe).where(Recipe.id == recipe_id).values(save_count=Recipe.save_count + 1))
            db.commit()
        db.refresh(recipe)
    return SaveOut(saved=True, saves=recipe.save_count)


@router.delete("/{recipe_id}/save", response_model=SaveOut)
def unsave_recipe(recipe_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = _get_recipe(db, recipe_id)
    saved = db.get(RecipeSave, (user.id, recipe_id))
    if saved is not None:
        db.delete(saved)
        db.execute(
            update(Recipe)
            .where(Recipe.id == recipe_id, Recipe.save_count > 0)
            .values(save_count=Recipe.save_count - 1)
        )
        db.commit()
        db.refresh(recipe)
    return SaveOut(saved=False, saves=recipe.save_count)


@router.get("/{recipe_id}/reviews", response_model=ReviewPage)
def list_reviews(
    recipe_id: int,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """레시피 상세의 '댓글 (N)'. 오래된 순."""
    _get_recipe(db, recipe_id)
    rows = db.scalars(
        select(Review)
        .options(joinedload(Review.author))
        .where(Review.recipe_id == recipe_id)
        .order_by(Review.created_at.asc(), Review.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return ReviewPage(
        total=count(db, Review, Review.recipe_id == recipe_id),
        items=[
            ReviewOut(
                id=r.id,
                recipe_id=r.recipe_id,
                author=user_brief(r.author),
                text=r.text,
                created_at=r.created_at,
                is_mine=r.author_id == user.id,
            )
            for r in rows
        ],
    )


@router.post("/{recipe_id}/reviews", response_model=ReviewOut, status_code=201)
def create_review(
    recipe_id: int,
    body: ReviewCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """레시피 상세 하단의 댓글 [등록]. 홈의 '내가 쓴 후기'에도 나와요."""
    _get_recipe(db, recipe_id)
    review = Review(recipe_id=recipe_id, author_id=user.id, text=body.text)
    db.add(review)
    db.flush()
    db.execute(update(Recipe).where(Recipe.id == recipe_id).values(comment_count=Recipe.comment_count + 1))
    db.commit()
    return ReviewOut(
        id=review.id,
        recipe_id=recipe_id,
        author=user_brief(user),
        text=review.text,
        created_at=review.created_at,
        is_mine=True,
    )
