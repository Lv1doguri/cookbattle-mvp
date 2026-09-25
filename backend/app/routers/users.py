from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ApiError
from ..models import Follow, Post, User
from ..schemas import FollowOut, PostPage, UserProfileOut
from ..security import get_current_user
from ..services.serialize import count, post_page, post_query, user_brief
from ..services.xp import level_for

router = APIRouter(prefix="/users", tags=["users"])


def _get_user(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise ApiError(404, "user_not_found", "사용자를 찾을 수 없습니다")
    return target


@router.get("/{user_id}", response_model=UserProfileOut)
def get_profile(user_id: int, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = _get_user(db, user_id)
    return UserProfileOut(
        **user_brief(target).model_dump(),
        bio=target.bio,
        level=level_for(target.xp),
        follower_count=count(db, Follow, Follow.followee_id == target.id),
        following_count=count(db, Follow, Follow.follower_id == target.id),
        post_count=count(db, Post, Post.author_id == target.id),
        is_following=db.get(Follow, (me.id, target.id)) is not None,
        is_me=target.id == me.id,
    )


@router.get("/{user_id}/posts", response_model=PostPage)
def user_posts(
    user_id: int,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user(db, user_id)
    stmt = post_query().where(Post.author_id == user_id).order_by(Post.id.desc())
    return post_page(db, stmt, me, limit, offset)


@router.post("/{user_id}/follow", response_model=FollowOut)
def follow(user_id: int, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == me.id:
        raise ApiError(400, "cannot_follow_self", "자기 자신은 팔로우할 수 없습니다")
    _get_user(db, user_id)
    if db.get(Follow, (me.id, user_id)) is None:
        db.add(Follow(follower_id=me.id, followee_id=user_id))
        try:
            db.commit()
        except IntegrityError:  # double tap raced with itself; already following is the desired end state
            db.rollback()
    return FollowOut(following=True, follower_count=count(db, Follow, Follow.followee_id == user_id))


@router.delete("/{user_id}/follow", response_model=FollowOut)
def unfollow(user_id: int, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_user(db, user_id)
    existing = db.get(Follow, (me.id, user_id))
    if existing is not None:
        db.delete(existing)
        db.commit()
    return FollowOut(following=False, follower_count=count(db, Follow, Follow.followee_id == user_id))
