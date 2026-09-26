"""내 정보 / 홈 / 튜토리얼 / 설정 / 메뉴(저장·최근 본 레시피)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import (
    Exchange, PointLog, Recipe, RecipeCompletion, RecipeReview, RecipeSave, RecipeView, Submission, User,
)
from ..schemas import ExchangeOut, PointLogOut, TutorialUpdate, UserOut, UserUpdate
from ..services import ratelimit
from ..services.accounts import validate_nickname
from ..services.battle import battle_points_for_user, compute_rankings
from ..services.recipes import recipes_out
from ..services.serializers import review_out, user_out
from ..services.storage import to_url
from ..timeutil import month_start_utc

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.patch("")
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """개인 정보 수정: 닉네임, 비밀번호(현재 비밀번호 필요), 알림 설정.
    비밀번호를 바꾸면 다른 기기의 로그인은 모두 풀리고, 응답의 새 access_token으로 계속 사용."""
    new_token = None
    if payload.nickname is not None and payload.nickname.strip() != user.nickname:
        user.nickname = validate_nickname(db, payload.nickname, email=user.email, exclude_user_id=user.id)
    if payload.new_password is not None:
        ratelimit.hit(f"pwchange:{user.id}", 5, 600, "비밀번호 변경 시도가 너무 많아요")
        if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다")
        user.password_hash = hash_password(payload.new_password)
        user.token_version = (user.token_version or 0) + 1
    if payload.notifications_enabled is not None:
        user.notifications_enabled = payload.notifications_enabled
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다")
    db.refresh(user)
    if payload.new_password is not None:
        new_token = create_access_token(user)
    return {"user": user_out(user), "access_token": new_token}


@router.patch("/tutorial", response_model=UserOut)
def update_tutorial(payload: TutorialUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """튜토리얼 진행 저장. 중간 이탈 시 step으로 이어보기, 건너뛰기/완료 시 completed=true.
    '다시 보기'는 {"step": 0, "completed": false}."""
    if payload.step is not None:
        user.tutorial_step = min(payload.step, rules.TUTORIAL_STEPS)
    if payload.completed is not None:
        user.tutorial_completed = payload.completed
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.get("/home")
def home(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """홈 탭: 프로필 + 이번 달 요리 횟수/절약 식비 + 대결 참가 이력 + 내가 쓴 후기."""
    since = month_start_utc()

    # 이번 달 요리 = 대결 참가 + 레시피 따라하기 완료
    costs = []
    month_subs = db.query(Submission).filter(Submission.user_id == user.id, Submission.created_at >= since).all()
    costs += [s.ingredient_cost for s in month_subs]
    month_done = (
        db.query(RecipeCompletion)
        .filter(RecipeCompletion.user_id == user.id, RecipeCompletion.created_at >= since)
        .all()
    )
    costs += [c.recipe.estimated_cost for c in month_done]
    saved = sum(max(rules.DELIVERY_AVG_PRICE - c, 0) for c in costs if c is not None)

    history = []
    subs = (
        db.query(Submission)
        .filter(Submission.user_id == user.id)
        .order_by(Submission.created_at.desc())
        .limit(30)  # 최근 30개까지
        .all()
    )
    for s in subs:
        b = s.battle
        rank = None
        if b.is_closed and not b.is_void and not s.is_hidden:
            rank = next((e.rank for e in compute_rankings(db, b) if e.submission.id == s.id), None)
        history.append({
            "battle_id": b.id,
            "kind": b.kind,
            "kind_label": rules.BATTLE_KINDS.get(b.kind, ""),
            "category_name": b.category.name,
            "start_date": b.start_date,
            "end_date": b.end_date,
            "submission_id": s.id,
            "title": s.title,
            "image_url": to_url(s.images[0].path) if s.images else "",
            "is_closed": b.is_closed,
            "is_void": b.is_void,
            "rank": rank,
            "points_earned": battle_points_for_user(db, b.id, user.id)["points_earned"],
        })

    reviews = (
        db.query(RecipeReview)
        .filter(RecipeReview.user_id == user.id)
        .order_by(RecipeReview.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "user": user_out(user),
        "this_month": {
            "cook_count": len(costs),
            "saved_money": saved,
            "delivery_avg_price": rules.DELIVERY_AVG_PRICE,
        },
        "history": history,
        "my_reviews": [review_out(r, user) for r in reviews],
    }


@router.get("/points", response_model=list[PointLogOut])
def my_points(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = (
        db.query(PointLog)
        .filter(PointLog.user_id == user.id)
        .order_by(PointLog.created_at.desc(), PointLog.id.desc())
        .all()
    )
    return [PointLogOut(points=l.points, reason=l.reason, ref=l.ref, memo=l.memo or "", created_at=l.created_at)
            for l in logs]


@router.get("/saved-recipes")
def saved_recipes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(RecipeSave)
        .filter(RecipeSave.user_id == user.id)
        .order_by(RecipeSave.created_at.desc())
        .all()
    )
    return recipes_out(db, user, [r.recipe for r in rows])


@router.get("/recipes")
def my_recipes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """내가 올린 레시피 (최신순)."""
    rows = db.query(Recipe).filter(Recipe.author_id == user.id).order_by(Recipe.created_at.desc()).all()
    return recipes_out(db, user, rows)


@router.get("/recent-recipes")
def recent_recipes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(RecipeView)
        .filter(RecipeView.user_id == user.id)
        .order_by(RecipeView.viewed_at.desc())
        .limit(20)
        .all()
    )
    return recipes_out(db, user, [r.recipe for r in rows])


@router.get("/exchanges", response_model=list[ExchangeOut])
def my_exchanges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Exchange).filter(Exchange.user_id == user.id).order_by(Exchange.created_at.desc()).all()
    return [ExchangeOut(id=e.id, item_id=e.item_id, item_name=e.item.name, price=e.price, created_at=e.created_at)
            for e in rows]
