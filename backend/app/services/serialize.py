"""Turns ORM rows into response models, batching the per-viewer lookups (liked/saved/following)
so a page of 20 posts costs a handful of queries instead of ~80."""
from typing import List, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from ..enums import CATEGORY_LABEL, TIER_LABEL
from ..models import Follow, Ingredient, Like, Post, Save, User
from ..schemas import MeOut, PostDetailOut, PostOut, PostPage, RecipeSummary, UserBrief
from .xp import progress_for


def user_brief(u: User) -> UserBrief:
    return UserBrief(
        id=u.id,
        nickname=u.nickname,
        handle=u.handle,
        tier=u.tier,
        tier_label=TIER_LABEL[u.tier] if u.tier else None,
    )


def photo_url(filename: str) -> str:
    return f"/uploads/{filename}"


def count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def build_me(db: Session, user: User) -> MeOut:
    return MeOut(
        **user_brief(user).model_dump(),
        email=user.email,
        bio=user.bio,
        needs_tier_selection=user.tier is None,
        coins=user.coins,
        progress=progress_for(user),
        follower_count=count(db, Follow, Follow.followee_id == user.id),
        following_count=count(db, Follow, Follow.follower_id == user.id),
        post_count=count(db, Post, Post.author_id == user.id),
    )


def post_query() -> Select:
    return select(Post).options(joinedload(Post.author), joinedload(Post.photo))


def build_post_outs(db: Session, posts: Sequence[Post], viewer: User) -> List[PostOut]:
    if not posts:
        return []
    ids = [p.id for p in posts]
    author_ids = {p.author_id for p in posts}

    liked = set(db.scalars(select(Like.post_id).where(Like.user_id == viewer.id, Like.post_id.in_(ids))))
    saved = set(db.scalars(select(Save.post_id).where(Save.user_id == viewer.id, Save.post_id.in_(ids))))
    following = set(
        db.scalars(
            select(Follow.followee_id).where(Follow.follower_id == viewer.id, Follow.followee_id.in_(author_ids))
        )
    )
    ingredient_counts = dict(
        db.execute(
            select(Ingredient.post_id, func.count()).where(Ingredient.post_id.in_(ids)).group_by(Ingredient.post_id)
        ).all()
    )

    return [
        PostOut(
            id=p.id,
            caption=p.caption,
            photo_url=photo_url(p.photo.filename),
            captured_at=p.photo.captured_at,
            created_at=p.created_at,
            category=p.category,
            category_label=CATEGORY_LABEL[p.category] if p.category else None,
            author=user_brief(p.author),
            recipe=RecipeSummary(
                title=p.title,
                cost_krw=p.cost_krw,
                cook_minutes=p.cook_minutes,
                difficulty=p.difficulty,
                difficulty_label=TIER_LABEL[p.difficulty],
                ingredient_count=ingredient_counts.get(p.id, 0),
            ),
            like_count=p.like_count,
            comment_count=p.comment_count,
            save_count=p.save_count,
            is_liked=p.id in liked,
            is_saved=p.id in saved,
            is_following_author=p.author_id in following,
            is_mine=p.author_id == viewer.id,
            battle_id=p.battle_id,
        )
        for p in posts
    ]


def build_post_detail(db: Session, post: Post, viewer: User) -> PostDetailOut:
    base = build_post_outs(db, [post], viewer)[0]
    return PostDetailOut(
        **base.model_dump(),
        author_follower_count=count(db, Follow, Follow.followee_id == post.author_id),
    )


def post_page(db: Session, stmt: Select, viewer: User, limit: int, offset: int) -> PostPage:
    rows = db.scalars(stmt.limit(limit + 1).offset(offset)).all()
    return PostPage(items=build_post_outs(db, rows[:limit], viewer), has_more=len(rows) > limit)
