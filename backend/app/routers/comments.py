from typing import List, Set

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..errors import ApiError
from ..models import Comment, CommentLike, Post, User
from ..schemas import CommentCreateIn, CommentLikeOut, CommentOut, CommentPage
from ..security import get_current_user
from ..services.serialize import count, user_brief

router = APIRouter(tags=["comments"])


def _out(c: Comment, viewer: User, liked_ids: Set[int]) -> CommentOut:
    return CommentOut(
        id=c.id,
        post_id=c.post_id,
        parent_id=c.parent_id,
        author=user_brief(c.author),
        text=c.text,
        created_at=c.created_at,
        like_count=c.like_count,
        is_liked=c.id in liked_ids,
        is_mine=c.author_id == viewer.id,
    )


def _get_comment(db: Session, comment_id: int) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise ApiError(404, "comment_not_found", "댓글을 찾을 수 없습니다")
    return comment


@router.get("/posts/{post_id}/comments", response_model=CommentPage)
def list_comments(
    post_id: int,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """오래된 댓글이 먼저. 답글은 parent_id로 원댓글에 붙어 있으니 프론트에서 묶어 보여주세요(답글은 1단계까지)."""
    if db.get(Post, post_id) is None:
        raise ApiError(404, "post_not_found", "게시물을 찾을 수 없습니다")
    rows: List[Comment] = list(
        db.scalars(
            select(Comment)
            .options(joinedload(Comment.author))
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .limit(limit)
            .offset(offset)
        )
    )
    ids = [c.id for c in rows]
    liked = (
        set(db.scalars(select(CommentLike.comment_id).where(CommentLike.user_id == user.id, CommentLike.comment_id.in_(ids))))
        if ids
        else set()
    )
    return CommentPage(items=[_out(c, user, liked) for c in rows], total=count(db, Comment, Comment.post_id == post_id))


@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    post_id: int,
    body: CommentCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.get(Post, post_id) is None:
        raise ApiError(404, "post_not_found", "게시물을 찾을 수 없습니다")

    parent_id = None
    if body.parent_id is not None:
        parent = db.get(Comment, body.parent_id)
        if parent is None or parent.post_id != post_id:
            raise ApiError(404, "comment_not_found", "답글을 달 댓글을 찾을 수 없습니다")
        parent_id = parent.parent_id or parent.id  # a reply to a reply attaches to the top-level comment

    comment = Comment(post_id=post_id, author_id=user.id, parent_id=parent_id, text=body.text)
    db.add(comment)
    db.flush()
    db.execute(update(Post).where(Post.id == post_id).values(comment_count=Post.comment_count + 1))
    db.commit()
    return _out(comment, user, set())


@router.post("/comments/{comment_id}/like", response_model=CommentLikeOut)
def like_comment(comment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comment = _get_comment(db, comment_id)
    if db.get(CommentLike, (user.id, comment_id)) is None:
        db.add(CommentLike(user_id=user.id, comment_id=comment_id))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
        else:
            db.execute(update(Comment).where(Comment.id == comment_id).values(like_count=Comment.like_count + 1))
            db.commit()
        db.refresh(comment)
    return CommentLikeOut(liked=True, like_count=comment.like_count)


@router.delete("/comments/{comment_id}/like", response_model=CommentLikeOut)
def unlike_comment(comment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comment = _get_comment(db, comment_id)
    like = db.get(CommentLike, (user.id, comment_id))
    if like is not None:
        db.delete(like)
        db.execute(
            update(Comment)
            .where(Comment.id == comment_id)
            .values(like_count=case((Comment.like_count > 0, Comment.like_count - 1), else_=0))
        )
        db.commit()
        db.refresh(comment)
    return CommentLikeOut(liked=False, like_count=comment.like_count)
