"""레시피 탭: 목록(검색·필터·정렬·재료로 찾기), 상세, 올리기/수정/삭제, 사진, 저장, 후기, 우승자 공유, 따라하기."""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import get_current_user
from ..database import get_db
from ..models import Recipe, RecipeCompletion, RecipeReview, RecipeSave, RecipeView, Submission, User
from ..schemas import CommentCreate, RecipeCreate, RecipeList, RecipeOut, RecipeUpdate, ReviewOut
from ..services import ratelimit
from ..services.battle import is_winner
from ..services.points import award
from ..services.recipes import RecipeFilter, recipe_fields, recipes_out, search, sort_results, split_csv
from ..services.serializers import recipe_out, review_out
from ..services.storage import delete_files, save_image
from ..timeutil import utcnow

router = APIRouter(tags=["recipes"])


def _get(db: Session, recipe_id: int) -> Recipe:
    r = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다")
    return r


def _filter_params(
    q: str = Query("", max_length=50, description="재료, 요리 이름, 키워드 (띄어쓰기 = 모두 포함)"),
    have: str = Query("", max_length=200, description="재료로 찾기: 가진 재료 쉼표 구분 (예: 계란,김치,밥)"),
    type: str = Query("", max_length=100, description="종류 쉼표 구분: rice,noodle,pasta,meat,soup,side,healthy,dessert"),
    difficulty: str = Query("", max_length=50, description="난이도 쉼표 구분: easy,normal,hard"),
    tag: str = Query("", max_length=100, description="태그 쉼표 구분 (모두 포함): 자취 필수,전자레인지,..."),
    min_cost: Optional[int] = Query(None, ge=0), max_cost: Optional[int] = Query(None, ge=0),
    min_minutes: Optional[int] = Query(None, ge=0), max_minutes: Optional[int] = Query(None, ge=0),
    source: Optional[str] = Query(None, pattern="^(official|winner|user)$"),
    sort: str = Query("latest", pattern="^(latest|popular|cheap|quick)$"),
) -> RecipeFilter:
    return RecipeFilter(
        q=q.strip(), have=split_csv(have), types=split_csv(type), difficulty=split_csv(difficulty),
        tags=split_csv(tag), min_cost=min_cost, max_cost=max_cost, min_minutes=min_minutes,
        max_minutes=max_minutes, source=source, sort=sort,
    )


def _owned(db: Session, recipe_id: int, user: User) -> Recipe:
    r = _get(db, recipe_id)
    if r.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="내가 올린 레시피만 수정·삭제할 수 있어요")
    return r


# ---- 목록 / 필터 ----

@router.get("/recipes/options")
def recipe_options():
    """필터 화면·레시피 올리기 화면을 그리는 데 필요한 선택지 (인증 불필요).
    각 칩의 params를 그대로 GET /recipes 쿼리에 붙이면 된다."""
    return {
        "food_types": [{"key": k, "label": v} for k, v in rules.RECIPE_FOOD_TYPES.items()],
        "difficulties": [{"key": k, "label": v} for k, v in rules.RECIPE_DIFFICULTIES.items()],
        "tags": rules.RECIPE_TAGS,
        "budgets": rules.RECIPE_BUDGET_OPTIONS,
        "times": rules.RECIPE_TIME_OPTIONS,
        "quick_filters": rules.RECIPE_QUICK_FILTERS,
        "sorts": [{"key": k, "label": v} for k, v in rules.RECIPE_SORTS.items()],
    }


@router.get("/recipes", response_model=RecipeList)
def list_recipes(
    f: RecipeFilter = Depends(_filter_params),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """레시피 목록 + 검색 + 필터 + 정렬. total은 필터에 맞는 전체 개수 ("8개 결과").
    have(재료로 찾기)를 주면 각 레시피에 matched/missing_ingredients가 붙고, 부족한 재료가 적은 순으로 정렬."""
    rows = search(db, f)
    saves = {}
    if f.sort == "popular" and rows:
        ids = [r.id for r, _, _ in rows]
        saves = dict(db.query(RecipeSave.recipe_id, func.count(RecipeSave.id))
                     .filter(RecipeSave.recipe_id.in_(ids)).group_by(RecipeSave.recipe_id).all())
    rows = sort_results(rows, f.sort, saves)
    return RecipeList(total=len(rows), items=recipes_out(db, user, rows[offset:offset + limit]))


@router.get("/recipes/count")
def count_recipes(f: RecipeFilter = Depends(_filter_params), db: Session = Depends(get_db),
                  _user: User = Depends(get_current_user)):
    """필터 화면 하단 '레시피 N개 보기' 버튼용 — 칩을 누를 때마다 가볍게 호출."""
    return {"total": len(search(db, f))}


@router.get("/recipes/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """상세 조회 — '최근 본 레시피'에 기록된다."""
    r = _get(db, recipe_id)
    view = db.query(RecipeView).filter(RecipeView.recipe_id == r.id, RecipeView.user_id == user.id).first()
    if view:
        view.viewed_at = utcnow()
    else:
        db.add(RecipeView(recipe_id=r.id, user_id=user.id))
    try:
        db.commit()
    except IntegrityError:  # 동시에 두 번 열었을 때 — 조회 기록은 이미 있으니 무시
        db.rollback()
    return recipe_out(r, db, user)


# ---- 올리기 / 수정 / 삭제 ----

@router.post("/recipes", response_model=RecipeOut)
def create_recipe(payload: RecipeCreate, official: bool = False, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """레시피 올리기 (로그인한 누구나). 사진은 만든 뒤 POST /recipes/{id}/image 로 1장 등록.
    관리자가 official=true로 올리면 '요리왕 공식' 레시피."""
    if official and not user.is_admin:
        raise HTTPException(status_code=403, detail="공식 레시피는 관리자만 올릴 수 있어요")
    ratelimit.hit(f"recipe:{user.id}", rules.RECIPE_UPLOADS_PER_HOUR, 3600, "레시피를 너무 많이 올렸어요")
    r = Recipe(**recipe_fields(payload), author_id=user.id, is_official=official)
    db.add(r)
    db.commit()
    db.refresh(r)
    return recipe_out(r, db, user)


@router.patch("/recipes/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, payload: RecipeUpdate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """내 레시피 수정 (바꿀 항목만). 재료를 바꾸면 예상 재료비도 다시 계산."""
    r = _owned(db, recipe_id, user)
    for k, v in recipe_fields(payload).items():
        setattr(r, k, v)
    r.updated_at = utcnow()
    db.commit()
    db.refresh(r)
    return recipe_out(r, db, user)


@router.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """내 레시피 삭제 (저장·후기·조회 기록도 함께 삭제). 따라하기로 받은 포인트는 회수하지 않음."""
    r = _owned(db, recipe_id, user)
    for model in (RecipeSave, RecipeView, RecipeReview, RecipeCompletion):
        db.query(model).filter(model.recipe_id == r.id).delete(synchronize_session=False)
    db.delete(r)
    db.commit()
    return {"deleted": True}


@router.post("/submissions/{submission_id}/recipe", response_model=RecipeOut)
def share_winner_recipe(submission_id: int, payload: RecipeCreate, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """리그 대결 우승자(1등)의 레시피 공유 → '○○ 대결 1등' 배지가 붙는다.
    대표 사진은 대결 사진으로 자동 설정 (POST /recipes/{id}/image로 교체 가능)."""
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail="작품을 찾을 수 없습니다")
    if s.user_id != user.id:
        raise HTTPException(status_code=403, detail="내 작품의 레시피만 공유할 수 있어요")
    if s.battle.kind == "fail":
        raise HTTPException(status_code=400, detail="망한 요리 대회 작품은 레시피로 공유할 수 없어요")
    if not s.battle.is_closed:
        raise HTTPException(status_code=400, detail="대결이 끝난 뒤에 공유할 수 있어요")
    if not is_winner(db, s):
        raise HTTPException(status_code=403, detail="대결 우승자만 레시피를 공유할 수 있어요")
    if db.query(Recipe.id).filter(Recipe.source_submission_id == s.id).first():
        raise HTTPException(status_code=400, detail="이미 레시피를 공유했어요")
    r = Recipe(
        **recipe_fields(payload), author_id=user.id, is_official=False, source_submission_id=s.id,
        image_path=s.images[0].path if s.images else None,
    )
    db.add(r)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 레시피를 공유했어요")
    db.refresh(r)
    return recipe_out(r, db, user)


@router.post("/recipes/{recipe_id}/image", response_model=RecipeOut)
def upload_recipe_image(recipe_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """레시피 사진 1장 등록/교체 (작성자 또는 관리자). EXIF(위치정보) 제거 후 저장."""
    r = _owned(db, recipe_id, user)
    r.image_path = save_image(file)  # 대결 사진과 공유될 수 있으므로 기존 파일은 지우지 않음
    r.updated_at = utcnow()
    db.commit()
    return recipe_out(r, db, user)


# ---- 저장 ----
@router.post("/recipes/{recipe_id}/save", response_model=RecipeOut)
def save_recipe(recipe_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _get(db, recipe_id)
    db.add(RecipeSave(recipe_id=r.id, user_id=user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # 이미 저장됨 → 그대로 성공 처리
    return recipe_out(r, db, user)


@router.delete("/recipes/{recipe_id}/save", response_model=RecipeOut)
def unsave_recipe(recipe_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _get(db, recipe_id)
    db.query(RecipeSave).filter(RecipeSave.recipe_id == r.id, RecipeSave.user_id == user.id).delete()
    db.commit()
    return recipe_out(r, db, user)


# ---- 후기(댓글) ----
@router.get("/recipes/{recipe_id}/reviews", response_model=list[ReviewOut])
def recipe_reviews(recipe_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get(db, recipe_id)
    rows = (
        db.query(RecipeReview)
        .filter(RecipeReview.recipe_id == recipe_id)
        .order_by(RecipeReview.created_at.desc(), RecipeReview.id.desc())
        .all()
    )
    return [review_out(r, user) for r in rows]


@router.post("/recipes/{recipe_id}/reviews", response_model=ReviewOut)
def add_review(recipe_id: int, payload: CommentCreate, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    _get(db, recipe_id)
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="내용을 입력해 주세요")
    rv = RecipeReview(recipe_id=recipe_id, user_id=user.id, content=content)
    db.add(rv)
    db.commit()
    db.refresh(rv)
    return review_out(rv, user)


@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rv = db.query(RecipeReview).filter(RecipeReview.id == review_id).first()
    if rv is None:
        raise HTTPException(status_code=404, detail="후기를 찾을 수 없습니다")
    if rv.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="내 후기만 삭제할 수 있어요")
    db.delete(rv)
    db.commit()
    return {"deleted": True}


@router.get("/reviews", response_model=list[ReviewOut])
def all_reviews(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """메뉴 > 후기 모음 (전체 사용자, 최신순)."""
    rows = (
        db.query(RecipeReview)
        .order_by(RecipeReview.created_at.desc(), RecipeReview.id.desc())
        .limit(limit)
        .all()
    )
    return [review_out(r, user) for r in rows]


# ---- 따라하기 완료 ----
@router.post("/recipes/{recipe_id}/complete", response_model=RecipeOut)
def complete_recipe(recipe_id: int, file: UploadFile = File(..., description="따라 만든 요리 사진"),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """따라하기 완료 인증 → +1P (레시피당 1회, 본인 레시피 제외). 홈의 '이번 달 요리 횟수'에도 포함."""
    r = _get(db, recipe_id)
    if r.author_id == user.id:
        raise HTTPException(status_code=400, detail="내 레시피는 완료 인증할 수 없어요")
    if db.query(RecipeCompletion).filter(RecipeCompletion.recipe_id == r.id,
                                         RecipeCompletion.user_id == user.id).first():
        raise HTTPException(status_code=400, detail="이미 완료 인증한 레시피예요")
    path = save_image(file)
    try:
        db.add(RecipeCompletion(recipe_id=r.id, user_id=user.id, image_path=path))
        award(db, user, rules.RECIPE_COMPLETE_POINTS, "recipe_complete", f"recipe:{r.id}",
              memo=f"'{r.title}' 따라하기 완료")
        db.commit()
    except IntegrityError:
        db.rollback()
        delete_files([path])
        raise HTTPException(status_code=400, detail="이미 완료 인증한 레시피예요")
    return recipe_out(r, db, user)
