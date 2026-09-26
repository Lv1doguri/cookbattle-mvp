"""레시피 검색·필터·정렬과 응답 변환 (디자인: 04 레시피 목록 / 05 필터 / 레시피 상세).

필터는 파이썬에서 처리한다: SQLite JSON 칸(재료·태그)은 한글이 \\uXXXX로 저장돼 LIKE 검색이 안 되고,
MVP 규모(수백 개)에서는 충분히 빠르다.
"""
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import rules
from ..models import Recipe, RecipeCompletion, RecipeReview, RecipeSave, User
from ..schemas import RecipeOut
from .storage import to_url


@dataclass
class RecipeFilter:
    q: str = ""  # 재료, 요리 이름, 키워드
    have: list = field(default_factory=list)  # 재료로 찾기: 가진 재료들
    types: list = field(default_factory=list)  # 종류 (여러 개 → 하나라도 맞으면)
    difficulty: list = field(default_factory=list)  # 난이도 (여러 개 → 하나라도)
    tags: list = field(default_factory=list)  # 태그 (여러 개 → 모두 포함)
    min_cost: Optional[int] = None
    max_cost: Optional[int] = None
    min_minutes: Optional[int] = None
    max_minutes: Optional[int] = None
    source: Optional[str] = None  # official | winner | user
    author_id: Optional[int] = None
    sort: str = "latest"


def split_csv(value: Optional[str]) -> list:
    return [x.strip() for x in (value or "").split(",") if x.strip()][:20]


def source_of(r: Recipe) -> str:
    if r.is_official:
        return "official"
    return "winner" if r.source_submission_id else "user"


def badge_of(r: Recipe) -> Optional[str]:
    if r.is_official:
        return "요리왕 공식"
    sub = r.source_submission
    if sub is not None and sub.battle is not None:
        return f"{sub.battle.category.name} 대결 1등"
    return None


def _ingredient_names(r: Recipe) -> list:
    return [str(i.get("name", "")).strip() for i in (r.ingredients or []) if isinstance(i, dict)]


def _matches_have(r: Recipe, have: list) -> tuple:
    """(가진 재료 중 쓰이는 것, 더 필요한 재료). 부분 일치 ('계란' ↔ '계란 2개')."""
    names = _ingredient_names(r)
    matched, missing = [], []
    for n in names:
        (matched if any(h in n or n in h for h in have) else missing).append(n)
    return matched, missing


def _text_hit(r: Recipe, q: str) -> bool:
    q = q.lower()
    hay = " ".join([r.title or "", r.description or "", " ".join(r.tags or []), " ".join(_ingredient_names(r)),
                    rules.RECIPE_FOOD_TYPES.get(r.food_type or "", "")]).lower()
    return all(word in hay for word in q.split())


def search(db: Session, f: RecipeFilter) -> list:
    """필터에 맞는 레시피 목록 → [(recipe, matched, missing)] (matched/missing은 재료로 찾기일 때만)."""
    query = db.query(Recipe)
    if f.source == "official":
        query = query.filter(Recipe.is_official.is_(True))
    elif f.source == "winner":
        query = query.filter(Recipe.source_submission_id.isnot(None), Recipe.is_official.is_(False))
    elif f.source == "user":
        query = query.filter(Recipe.source_submission_id.is_(None), Recipe.is_official.is_(False))
    if f.author_id is not None:
        query = query.filter(Recipe.author_id == f.author_id)
    if f.types:
        query = query.filter(Recipe.food_type.in_(f.types))
    if f.difficulty:
        query = query.filter(Recipe.difficulty.in_(f.difficulty))
    if f.min_cost is not None:
        query = query.filter(Recipe.estimated_cost >= f.min_cost)
    if f.max_cost is not None:
        query = query.filter(Recipe.estimated_cost <= f.max_cost)
    if f.min_minutes is not None:
        query = query.filter(Recipe.cook_minutes >= f.min_minutes)
    if f.max_minutes is not None:
        query = query.filter(Recipe.cook_minutes <= f.max_minutes)

    out = []
    for r in query.order_by(Recipe.created_at.desc(), Recipe.id.desc()).all():
        if f.tags and not all(t in (r.tags or []) for t in f.tags):
            continue
        if f.q and not _text_hit(r, f.q):
            continue
        matched = missing = None
        if f.have:
            matched, missing = _matches_have(r, f.have)
            if not matched:
                continue
        out.append((r, matched, missing))
    return out


def sort_results(rows: list, sort: str, save_counts: dict) -> list:
    """latest(기본, 이미 최신순) | popular | cheap | quick. 재료로 찾기면 '부족한 재료 적은 순'이 먼저."""
    big = 10 ** 9
    if sort == "popular":
        rows.sort(key=lambda x: -save_counts.get(x[0].id, 0))
    elif sort == "cheap":
        rows.sort(key=lambda x: x[0].estimated_cost if x[0].estimated_cost is not None else big)
    elif sort == "quick":
        rows.sort(key=lambda x: x[0].cook_minutes if x[0].cook_minutes is not None else big)
    if rows and rows[0][2] is not None:  # 재료로 찾기
        rows.sort(key=lambda x: (len(x[2]), -len(x[1])))
    return rows


def _count_map(db: Session, model, ids: list) -> dict:
    if not ids:
        return {}
    rows = db.query(model.recipe_id, func.count(model.id)).filter(model.recipe_id.in_(ids)).group_by(model.recipe_id)
    return dict(rows.all())


def _mine_set(db: Session, model, ids: list, user: User) -> set:
    if not ids:
        return set()
    return {rid for (rid,) in db.query(model.recipe_id).filter(model.recipe_id.in_(ids), model.user_id == user.id)}


def recipes_out(db: Session, user: User, rows: list) -> list:
    """여러 레시피를 한 번에 변환 (저장 수 등은 묶어서 조회 → 카드마다 쿼리하지 않음).
    rows: [recipe] 또는 [(recipe, matched, missing)]"""
    rows = [x if isinstance(x, tuple) else (x, None, None) for x in rows]
    ids = [r.id for r, _, _ in rows]
    saves = _count_map(db, RecipeSave, ids)
    reviews = _count_map(db, RecipeReview, ids)
    dones = _count_map(db, RecipeCompletion, ids)
    my_saves = _mine_set(db, RecipeSave, ids, user)
    my_dones = _mine_set(db, RecipeCompletion, ids, user)
    return [
        RecipeOut(
            id=r.id,
            title=r.title,
            description=r.description or "",
            ingredients=[
                {"name": i.get("name", ""), "amount": i.get("amount", ""), "price": i.get("price")}
                for i in (r.ingredients or []) if isinstance(i, dict)
            ],
            steps=list(r.steps or []),
            estimated_cost=r.estimated_cost,
            cook_minutes=r.cook_minutes,
            difficulty=r.difficulty,
            difficulty_label=rules.RECIPE_DIFFICULTIES.get(r.difficulty or "", ""),
            food_type=r.food_type,
            food_type_label=rules.RECIPE_FOOD_TYPES.get(r.food_type or "", ""),
            tags=list(r.tags or []),
            tools=r.tools or "",
            source=source_of(r),
            badge=badge_of(r),
            author_id=r.author_id,
            author_nickname=r.author.nickname if r.author else ("요리왕" if r.is_official else None),
            is_official=r.is_official,
            is_mine=r.author_id == user.id,
            source_submission_id=r.source_submission_id,
            image_url=to_url(r.image_path) or None,
            save_count=saves.get(r.id, 0),
            review_count=reviews.get(r.id, 0),
            completion_count=dones.get(r.id, 0),
            saved_by_me=r.id in my_saves,
            completed_by_me=r.id in my_dones,
            matched_ingredients=matched,
            missing_ingredients=missing,
            created_at=r.created_at,
        )
        for r, matched, missing in rows
    ]


def recipe_fields(payload) -> dict:
    """생성/수정 요청 → DB 칸. 재료 가격이 하나라도 있으면 예상 재료비 = 합계."""
    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        data["title"] = data["title"].strip()
    if "ingredients" in data:
        ings = [{"name": i["name"].strip(), "amount": (i.get("amount") or "").strip(), "price": i.get("price")}
                for i in data["ingredients"]]
        data["ingredients"] = ings
        prices = [i["price"] for i in ings if i["price"] is not None]
        data["estimated_cost"] = sum(prices) if prices else None
    return data
