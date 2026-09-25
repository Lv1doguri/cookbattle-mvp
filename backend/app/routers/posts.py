from fastapi import APIRouter, Depends
from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import clock
from ..content import BASE_POST_COINS, BASE_POST_XP, DAILY_BASE_REWARD_LIMIT, LIKE_XP, PHOTO_TTL
from ..database import get_db
from ..errors import ApiError
from ..models import Battle, Ingredient, Like, Photo, Post, Save, Step, User
from ..schemas import LikeOut, PostCreatedOut, PostCreateIn, PostDetailOut, RewardOut, SaveOut
from ..security import get_current_user
from ..services.serialize import build_post_detail, count, post_query
from ..services.xp import grant, level_for, progress_for

router = APIRouter(prefix="/posts", tags=["posts"])


def _get_post(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise ApiError(404, "post_not_found", "게시물을 찾을 수 없습니다")
    return post


@router.post("", response_model=PostCreatedOut, status_code=201)
def create_post(body: PostCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """카메라 → 작성 → [게시]. body.battle_id를 주면 오늘의 대결 참가로 등록돼요."""
    now = clock.utcnow()

    photo = db.get(Photo, body.photo_id)
    if photo is None or photo.user_id != user.id:
        raise ApiError(404, "photo_not_found", "사진을 찾을 수 없습니다")
    if db.scalar(select(Post.id).where(Post.photo_id == photo.id)) is not None:
        raise ApiError(409, "photo_already_used", "이미 게시한 사진이에요")
    if now > photo.captured_at + PHOTO_TTL:
        raise ApiError(400, "photo_expired", "촬영한 지 너무 오래됐어요. 다시 촬영해주세요")

    battle = None
    if body.battle_id is not None:
        battle = db.get(Battle, body.battle_id)
        if battle is None:
            raise ApiError(404, "battle_not_found", "대결을 찾을 수 없습니다")
        if user.tier is None:
            raise ApiError(400, "tier_not_selected", "먼저 요리 실력을 선택해주세요")
        if battle.tier != user.tier:
            raise ApiError(403, "wrong_tier", "내 실력 단계의 대결에만 참여할 수 있어요")
        if not (battle.starts_at <= now < battle.ends_at):
            raise ApiError(400, "battle_closed", "마감된 대결이에요")
        if db.scalar(select(Post.id).where(Post.battle_id == battle.id, Post.author_id == user.id)) is not None:
            raise ApiError(409, "already_entered", "이미 이 대결에 참여했어요")

    daily_limit_reached = False
    if battle is not None:
        xp, coins, score = battle.reward_xp, battle.reward_coins, battle.reward_xp
    else:
        day_start, _ = clock.kst_day_bounds(clock.kst_date(now))
        rewarded_today = count(
            db, Post, Post.author_id == user.id, Post.battle_id.is_(None), Post.reward_xp > 0, Post.created_at >= day_start
        )
        if rewarded_today < DAILY_BASE_REWARD_LIMIT:
            xp, coins = BASE_POST_XP, BASE_POST_COINS
        else:
            xp, coins, daily_limit_reached = 0, 0, True
        score = 0

    level_before = level_for(user.xp)
    post = Post(
        author_id=user.id,
        photo_id=photo.id,
        battle_id=battle.id if battle else None,
        caption=body.caption,
        title=body.title,
        category=body.category,
        cost_krw=body.cost_krw,
        cook_minutes=body.cook_minutes,
        difficulty=body.difficulty,
        battle_score=score,
        reward_xp=xp,
        reward_coins=coins,
        created_at=now,
    )
    post.ingredients = [Ingredient(position=i, name=ing.name, amount=ing.amount) for i, ing in enumerate(body.ingredients)]
    post.steps = [Step(position=i + 1, text=s.text) for i, s in enumerate(body.steps)]
    db.add(post)
    try:
        db.flush()
    except IntegrityError:  # the same photo / same battle submitted twice at once
        db.rollback()
        raise ApiError(409, "duplicate_submission", "이미 처리된 요청이에요")

    if xp or coins:
        grant(db, user, xp=xp, coins=coins, reason="battle_entry" if battle else "post", ref_type="post", ref_id=post.id)
    db.commit()

    return PostCreatedOut(
        post=build_post_detail(db, post, user),
        reward=RewardOut(
            xp=xp,
            coins=coins,
            is_battle_entry=battle is not None,
            daily_limit_reached=daily_limit_reached,
            leveled_up=level_for(user.xp) > level_before,
        ),
        progress=progress_for(user),
        coins=user.coins,
    )


@router.get("/{post_id}", response_model=PostDetailOut)
def get_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.scalar(post_query().where(Post.id == post_id))
    if post is None:
        raise ApiError(404, "post_not_found", "게시물을 찾을 수 없습니다")
    return build_post_detail(db, post, user)


@router.post("/{post_id}/like", response_model=LikeOut)
def like_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _get_post(db, post_id)
    if db.get(Like, (user.id, post_id)) is None:
        # Battle entries earn XP from likes by other people, only while the battle is still open.
        pays_xp = False
        if post.battle_id is not None and post.author_id != user.id:
            pays_xp = clock.utcnow() < db.get(Battle, post.battle_id).ends_at
        db.add(Like(user_id=user.id, post_id=post_id, xp_granted=pays_xp))
        try:
            db.flush()
        except IntegrityError:  # double tap: the other request already liked it
            db.rollback()
        else:
            values = {"like_count": Post.like_count + 1}
            if pays_xp:
                values["battle_score"] = Post.battle_score + LIKE_XP
            db.execute(update(Post).where(Post.id == post_id).values(**values))
            if pays_xp:
                grant(db, post.author, xp=LIKE_XP, reason="like_received", ref_type="post", ref_id=post_id)
            db.commit()
        db.refresh(post)
    return LikeOut(liked=True, like_count=post.like_count)


@router.delete("/{post_id}/like", response_model=LikeOut)
def unlike_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _get_post(db, post_id)
    like = db.get(Like, (user.id, post_id))
    if like is not None:
        values = {"like_count": case((Post.like_count > 0, Post.like_count - 1), else_=0)}
        if like.xp_granted:
            values["battle_score"] = case((Post.battle_score >= LIKE_XP, Post.battle_score - LIKE_XP), else_=0)
        db.delete(like)
        db.execute(update(Post).where(Post.id == post_id).values(**values))
        if like.xp_granted:
            grant(db, post.author, xp=-LIKE_XP, reason="like_revoked", ref_type="post", ref_id=post_id)
        db.commit()
        db.refresh(post)
    return LikeOut(liked=False, like_count=post.like_count)


@router.post("/{post_id}/save", response_model=SaveOut)
def save_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _get_post(db, post_id)
    if db.get(Save, (user.id, post_id)) is None:
        db.add(Save(user_id=user.id, post_id=post_id))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
        else:
            db.execute(update(Post).where(Post.id == post_id).values(save_count=Post.save_count + 1))
            db.commit()
        db.refresh(post)
    return SaveOut(saved=True, save_count=post.save_count)


@router.delete("/{post_id}/save", response_model=SaveOut)
def unsave_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _get_post(db, post_id)
    saved = db.get(Save, (user.id, post_id))
    if saved is not None:
        db.delete(saved)
        db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(save_count=case((Post.save_count > 0, Post.save_count - 1), else_=0))
        )
        db.commit()
        db.refresh(post)
    return SaveOut(saved=False, save_count=post.save_count)
