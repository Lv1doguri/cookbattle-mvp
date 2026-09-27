from typing import List, Optional, Sequence

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, joinedload

from ..enums import CATEGORY_LABEL, TIER_LABEL, TOOL_LABEL, Budget, Category, CookTime, Tier, Tool
from ..models import Ingredient, Recipe, RecipeSave, RecipeTool, User
from ..schemas import IngredientOut, RecipeCard, RecipeDetailOut, RecipePage, StepOut, ToolOut
from .accounts import user_brief
from .images import image_url


def recipe_query() -> Select:
    return select(Recipe).options(joinedload(Recipe.author))


def build_cards(db: Session, recipes: Sequence[Recipe], viewer: User) -> List[RecipeCard]:
    if not recipes:
        return []
    ids = [r.id for r in recipes]
    saved = set(db.scalars(select(RecipeSave.recipe_id).where(RecipeSave.user_id == viewer.id, RecipeSave.recipe_id.in_(ids))))
    return [
        RecipeCard(
            id=r.id,
            name=r.title,
            category=r.category,
            category_label=CATEGORY_LABEL[r.category],
            price=r.cost_krw,
            minutes=r.cook_minutes,
            difficulty=r.difficulty,
            difficulty_label=TIER_LABEL[r.difficulty],
            win_label=r.win_label,
            photo_url=image_url(r.photo_filename),
            saves=r.save_count,
            is_saved=r.id in saved,
            is_essential=r.is_essential,
        )
        for r in recipes
    ]


def build_detail(db: Session, recipe: Recipe, viewer: User) -> RecipeDetailOut:
    card = build_cards(db, [recipe], viewer)[0]
    return RecipeDetailOut(
        **card.model_dump(),
        author=user_brief(recipe.author),
        tools=[ToolOut(code=t, label=TOOL_LABEL[t]) for t in sorted((rt.tool for rt in recipe.tools), key=list(Tool).index)],
        ingredients=[IngredientOut(name=i.name, amount=i.amount) for i in recipe.ingredients],
        steps=[StepOut(order=s.position, text=s.text) for s in recipe.steps],
        comment_count=recipe.comment_count,
        created_at=recipe.created_at,
    )


def recipe_page(db: Session, stmt: Select, viewer: User, limit: int, offset: int, total: int) -> RecipePage:
    rows = db.scalars(stmt.limit(limit + 1).offset(offset)).all()
    return RecipePage(total=total, items=build_cards(db, rows[:limit], viewer), has_more=len(rows) > limit)


def _budget_clause(b: Budget):
    if b == Budget.under_5000:
        return Recipe.cost_krw <= 5000
    if b == Budget.between_5000_10000:
        return and_(Recipe.cost_krw > 5000, Recipe.cost_krw <= 10000)
    return Recipe.cost_krw > 10000


def _time_clause(t: CookTime):
    if t == CookTime.le_10:
        return Recipe.cook_minutes <= 10
    if t == CookTime.le_15:
        return Recipe.cook_minutes <= 15
    if t == CookTime.le_30:
        return Recipe.cook_minutes <= 30
    return Recipe.cook_minutes >= 60


def apply_filters(
    stmt: Select,
    *,
    q: Optional[str],
    categories: Optional[Sequence[Category]],
    budgets: Optional[Sequence[Budget]],
    times: Optional[Sequence[CookTime]],
    difficulties: Optional[Sequence[Tier]],
    tools: Optional[Sequence[Tool]],
    essential: Optional[bool] = None,
) -> Select:
    """Different filter groups are ANDed; several picks inside one group are ORed."""
    term = (q or "").strip()
    if term:
        stmt = stmt.where(
            or_(
                Recipe.title.icontains(term, autoescape=True),
                Recipe.win_label.icontains(term, autoescape=True),
                Recipe.id.in_(select(Ingredient.recipe_id).where(Ingredient.name.icontains(term, autoescape=True))),
            )
        )
    if categories:
        stmt = stmt.where(Recipe.category.in_(categories))
    if budgets:
        stmt = stmt.where(or_(*[_budget_clause(b) for b in budgets]))
    if times:
        stmt = stmt.where(or_(*[_time_clause(t) for t in times]))
    if difficulties:
        stmt = stmt.where(Recipe.difficulty.in_(difficulties))
    if tools:
        stmt = stmt.where(Recipe.id.in_(select(RecipeTool.recipe_id).where(RecipeTool.tool.in_(tools))))
    if essential:
        stmt = stmt.where(Recipe.is_essential.is_(True))
    return stmt
