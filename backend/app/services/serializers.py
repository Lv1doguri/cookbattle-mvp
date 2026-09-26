"""DB 객체 -> 응답 스키마 변환."""
import datetime as dt
from typing import Optional

from sqlalchemy.orm import Session

from .. import rules
from ..models import (
    Battle, Comment, Recipe, RecipeReview, Submission, User, Vote,
)
from ..schemas import (
    AICheckOut, BattleCommentOut, BattleOut, CategoryOut, CommentOut, RatingSummary, RecipeOut, ReviewOut, SubmissionImageOut,
    SubmissionOut, UserOut,
)
from .battle import days_left, is_open_for_entries, phase_days_left, vote_block_reason
from .shots import shot_label
from .storage import to_url
from ..timeutil import to_local_str


def user_out(u: User) -> UserOut:
    total = u.total_points or 0
    return UserOut(
        id=u.id,
        email=u.email,
        nickname=u.nickname,
        skill=u.skill,
        skill_label=rules.skill_label(u.skill),
        level=u.level,
        total_points=total,
        points=u.points or 0,
        next_level_points=rules.next_level_points(total),
        points_to_next_level=rules.next_level_points(total) - total,
        level_progress=rules.level_progress(total),
        is_admin=u.is_admin,
        invite_code=u.invite_code,
        tutorial_step=u.tutorial_step or 0,
        tutorial_completed=u.tutorial_completed,
        notifications_enabled=u.notifications_enabled,
    )


def battle_out(b: Battle, db: Session, user: User) -> BattleOut:
    count = (
        db.query(Submission)
        .filter(Submission.battle_id == b.id, Submission.is_hidden.is_(False))
        .count()
    )
    submitted = (
        db.query(Submission.id).filter(Submission.battle_id == b.id, Submission.user_id == user.id).first()
        is not None
    )
    voted = db.query(Vote.id).filter(Vote.battle_id == b.id, Vote.voter_id == user.id).first() is not None
    block = vote_block_reason(db, b, user)
    is_fail = b.kind == "fail"
    return BattleOut(
        id=b.id,
        kind=b.kind or "league",
        kind_label=rules.BATTLE_KINDS.get(b.kind or "league", ""),
        group=b.group,
        group_label="전체" if is_fail else rules.skill_label(b.group),
        category=CategoryOut(id=b.category.id, name=b.category.name, description=b.category.description or ""),
        start_date=b.start_date,
        cooking_end_date=b.voting_starts - dt.timedelta(days=1),
        vote_start_date=b.voting_starts,
        end_date=b.end_date,
        phase=b.phase,
        phase_label=rules.PHASE_LABELS[b.phase],
        phase_days_left=phase_days_left(b),
        days_left=days_left(b),
        verification_keyword=b.verification_keyword,
        is_closed=b.is_closed,
        is_void=b.is_void,
        submission_count=count,
        has_submitted=submitted,
        has_voted=voted,
        can_submit=is_open_for_entries(b) and not submitted and (is_fail or b.group == user.skill),
        can_vote=block is None,
        vote_block_reason=block,
        is_my_group=is_fail or b.group == user.skill,
    )


def show_votes(b: Battle) -> bool:
    return b.is_closed or not rules.HIDE_VOTES_UNTIL_CLOSED


def submission_out(s: Submission, db: Session, user: User, votes: int, my_vote_id: Optional[int]) -> SubmissionOut:
    urls = [to_url(i.path) for i in s.images]
    summary = rating_summary(db, s.id)
    return SubmissionOut(
        id=s.id,
        battle_id=s.battle_id,
        user_id=s.user_id,
        nickname=s.user.nickname,
        user_level=s.user.level,
        title=s.title,
        description=s.description or "",
        ingredient_cost=s.ingredient_cost,
        image_url=urls[0] if urls else "",
        image_urls=urls,
        images=[
            SubmissionImageOut(
                url=to_url(i.path), shot_type=i.shot_type,
                shot_label=shot_label(i.shot_type) if i.shot_type else "", time_verified=i.taken_at is not None,
            )
            for i in s.images
        ],
        photo_verified=bool(s.images) and all(i.taken_at is not None for i in s.images),
        ai_verified=s.ai_status == "passed",
        ai_check=AICheckOut(
            status=s.ai_status,
            summary=(s.ai_result or {}).get("summary", ""),
            warnings=(s.ai_result or {}).get("problems", []),
        ) if s.ai_status else None,
        created_at=s.created_at,
        vote_count=votes if show_votes(s.battle) else None,
        has_voted=my_vote_id == s.id,
        is_mine=s.user_id == user.id,
        is_hidden=s.is_hidden,
        comment_count=db.query(Comment).filter(Comment.submission_id == s.id).count(),
        rating_avg=summary.average,
        rating_count=summary.count,
    )


def my_vote_submission_id(db: Session, battle_id: int, user: User) -> Optional[int]:
    v = db.query(Vote).filter(Vote.battle_id == battle_id, Vote.voter_id == user.id).first()
    return v.submission_id if v else None


def rating_summary(db: Session, submission_id: int) -> RatingSummary:
    ratings = [
        r for (r,) in db.query(Comment.rating)
        .filter(Comment.submission_id == submission_id, Comment.rating.isnot(None))
        .all()
    ]
    dist = {str(n): ratings.count(n) for n in (5, 4, 3, 2, 1)}
    avg = round(sum(ratings) / len(ratings), 1) if ratings else None
    return RatingSummary(average=avg, count=len(ratings), distribution=dist)


def battle_comment_out(c: Comment, user: User) -> BattleCommentOut:
    return BattleCommentOut(
        id=c.id,
        submission_id=c.submission_id,
        user_id=c.user_id,
        nickname=c.user.nickname,
        content=c.content,
        rating=c.rating,
        created_at=c.created_at,
        created_at_display=to_local_str(c.created_at),
        is_edited=c.updated_at is not None,
        is_mine=c.user_id == user.id,
    )


def comment_out(c: Comment, user: User) -> CommentOut:
    return CommentOut(
        id=c.id, user_id=c.user_id, nickname=c.user.nickname, content=c.content,
        created_at=c.created_at, is_mine=c.user_id == user.id,
    )


def recipe_out(r: Recipe, db: Session, user: User) -> RecipeOut:
    from .recipes import recipes_out  # 순환 import 방지
    return recipes_out(db, user, [r])[0]


def review_out(rv: RecipeReview, user: User) -> ReviewOut:
    return ReviewOut(
        id=rv.id, recipe_id=rv.recipe_id, recipe_title=rv.recipe.title, user_id=rv.user_id,
        nickname=rv.user.nickname, content=rv.content, created_at=rv.created_at, is_mine=rv.user_id == user.id,
    )
