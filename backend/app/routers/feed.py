from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Follow, Post, User
from ..schemas import PostPage
from ..security import get_current_user
from ..services.serialize import post_page, post_query

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=PostPage)
def feed(
    tab: Literal["recommended", "following"] = "recommended",
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """홈 피드. recommended = 모든 사람의 최신 게시물, following = 내가 팔로우한 사람들의 게시물."""
    stmt = post_query()
    if tab == "following":
        stmt = stmt.where(Post.author_id.in_(select(Follow.followee_id).where(Follow.follower_id == user.id)))
    return post_page(db, stmt.order_by(Post.id.desc()), user, limit, offset)
