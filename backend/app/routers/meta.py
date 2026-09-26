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
            "participation": rules.PARTICIPATION_POINTS,
            "rank": rules.RANK_POINTS,
            "per_level": rules.POINTS_PER_LEVEL,
            "recipe_complete": rules.RECIPE_COMPLETE_POINTS,
            "streak_weeks": rules.STREAK_WEEKS,
            "streak_bonus": rules.STREAK_BONUS,
            "invite_inviter": rules.INVITE_POINTS_INVITER,
            "invite_invitee": rules.INVITE_POINTS_INVITEE,
        },
        "battle": {
            "duration_days": rules.BATTLE_DURATION_DAYS,
            "min_participants": rules.MIN_PARTICIPANTS,
            "hide_votes_until_closed": rules.HIDE_VOTES_UNTIL_CLOSED,
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
