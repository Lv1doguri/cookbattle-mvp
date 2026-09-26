"""First-run content: shop items, the official account, and sample recipes (idempotent)."""
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .content import ESSENTIAL_RECIPES, OFFICIAL_EMAIL, OFFICIAL_NICKNAME, RECIPE_SEED, SHOP_SEED
from .enums import Tier
from .models import Ingredient, Recipe, RecipeTool, ShopItem, Step, User
from .security import hash_password


def seed_all(db: Session) -> None:
    _seed_shop(db)
    _seed_recipes(db)


def _seed_shop(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(ShopItem)) != 0:
        return
    for name, price, required_level in SHOP_SEED:
        db.add(ShopItem(name=name, price_points=price, required_level=required_level))
    db.commit()


def _seed_recipes(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Recipe)) != 0:
        return
    official = db.scalar(select(User).where(User.email == OFFICIAL_EMAIL))
    if official is None:
        # Nobody knows this password (random, never stored anywhere), so the account can't be logged into.
        official = User(
            email=OFFICIAL_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            nickname=OFFICIAL_NICKNAME,
            tier=Tier.advanced,
        )
        db.add(official)
        db.flush()

    for title, category, cost, minutes, difficulty, win_label, tools, ingredients, steps in RECIPE_SEED:
        recipe = Recipe(
            author_id=official.id,
            title=title,
            category=category,
            cost_krw=cost,
            cook_minutes=minutes,
            difficulty=difficulty,
            win_label=win_label,
            is_essential=title in ESSENTIAL_RECIPES,
        )
        recipe.ingredients = [Ingredient(position=i, name=n, amount=a) for i, (n, a) in enumerate(ingredients)]
        recipe.steps = [Step(position=i + 1, text=t) for i, t in enumerate(steps)]
        recipe.tools = [RecipeTool(tool=t) for t in tools]
        db.add(recipe)
    db.commit()
