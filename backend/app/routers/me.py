from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ApiError
from ..models import Like, Post, Save, User
from ..schemas import MeOut, PostPage, ProfileUpdateIn, TierIn
from ..security import get_current_user
from ..services.serialize import build_me, post_page, post_query

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeOut)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_me(db, user)


@router.patch("", response_model=MeOut)
def update_me(body: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.handle is not None and body.handle != user.handle:
        if db.scalar(select(User.id).where(User.handle == body.handle)) is not None:
            raise ApiError(409, "handle_taken", "이미 사용 중인 아이디입니다")
        user.handle = body.handle
    if body.nickname is not None:
        user.nickname = body.nickname
    if body.bio is not None:
        user.bio = body.bio
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "handle_taken", "이미 사용 중인 아이디입니다")
    return build_me(db, user)


@router.put("/tier", response_model=MeOut)
def select_tier(body: TierIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """'나의 요리 실력을 선택해주세요' 화면의 [선택 완료]."""
    user.tier = body.tier
    db.commit()
    return build_me(db, user)


@router.get("/likes", response_model=PostPage)
def my_liked_posts(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        post_query()
        .join(Like, Like.post_id == Post.id)
        .where(Like.user_id == user.id)
        .order_by(Like.created_at.desc(), Post.id.desc())
    )
    return post_page(db, stmt, user, limit, offset)


@router.get("/saved", response_model=PostPage)
def my_saved_posts(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        post_query()
        .join(Save, Save.post_id == Post.id)
        .where(Save.user_id == user.id)
        .order_by(Save.created_at.desc(), Post.id.desc())
    )
    return post_page(db, stmt, user, limit, offset)
