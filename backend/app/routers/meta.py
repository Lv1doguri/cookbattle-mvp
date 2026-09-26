from fastapi import APIRouter

from .. import rules
from ..config import settings
from ..services.ai_vision import is_enabled

router = APIRouter(tags=["meta"])


@router.get("/meta")
def meta():
    """라벨/규칙값 (인증 불필요). 프론트에서 하드코딩하지 말고 이걸 사용."""
    return {
        "skills": rules.SKILLS,
        "points": {
            "signup_bonus": rules.SIGNUP_BONUS,
            "first_battle_bonus": rules.FIRST_BATTLE_BONUS,
            "participation": rules.PARTICIPATION_POINTS,
            "vote": rules.VOTE_POINTS,
            "rank": rules.RANK_POINTS,
            "rank_fail": rules.FAIL_RANK_POINTS,
            "rank_full_min_participants": rules.RANK_FULL_MIN_PARTICIPANTS,
            "level_thresholds": rules.LEVEL_THRESHOLDS,
            "recipe_complete": rules.RECIPE_COMPLETE_POINTS,
            "recipe_review": rules.RECIPE_REVIEW_POINTS,
            "recipe_review_daily_cap": rules.RECIPE_REVIEW_DAILY_CAP,
            "streak_weeks": rules.STREAK_WEEKS,
            "streak_bonus": rules.STREAK_BONUS,
            "invite_inviter": rules.INVITE_POINTS_INVITER,
            "invite_invitee": rules.INVITE_POINTS_INVITEE,
            "expiry_days": rules.POINT_EXPIRY_DAYS,
        },
        "battle": {
            "league_cooking_days": rules.LEAGUE_COOKING_DAYS,
            "league_vote_days": rules.LEAGUE_VOTE_DAYS,
            "fail_cooking_days": rules.FAIL_COOKING_DAYS,
            "fail_vote_days": rules.FAIL_VOTE_DAYS,
            "min_participants": rules.MIN_PARTICIPANTS,
            "hide_votes_until_closed": rules.HIDE_VOTES_UNTIL_CLOSED,
        },
        "shop": {
            "max_exchanges_per_month_per_user": rules.MAX_EXCHANGES_PER_MONTH_PER_USER,
        },
        "photos": {
            "shot_types": rules.SHOT_TYPES,
            "fixed_shots": rules.SHOT_FIXED,
            "random_shot_count": rules.SHOT_RANDOM_COUNT,
            "min_side": rules.PHOTO_MIN_SIDE,
            "max_bytes": rules.MAX_FILE_SIZE_BYTES,
        },
        "delivery_avg_price": rules.DELIVERY_AVG_PRICE,
        "tutorial_steps": rules.TUTORIAL_STEPS,
        "ai_check": {"enabled": is_enabled(), "mode": settings.ai_check_mode},
    }
