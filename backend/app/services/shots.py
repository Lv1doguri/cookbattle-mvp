"""다중 구도 촬영 가이드.

사용자마다 대결별로 필요한 구도가 정해진다:
  고정 구도(SHOT_FIXED) + 랜덤 구도(SHOT_RANDOM_POOL에서 SHOT_RANDOM_COUNT개)
랜덤은 (서버 비밀키, 대결, 사용자)로 시드를 만들어 새로고침해도 같고, 사람마다·대결마다 다르다.
→ 미리 찍어 둔 사진이나 인터넷 사진으로 '이번에 요구된 구도 조합'을 맞추기 어렵게 만든다.
"""
import hashlib
import random

from .. import rules
from ..config import settings
from ..models import Battle, User


def required_shots(battle: Battle, user: User) -> list:
    seed = hashlib.sha256(f"{settings.jwt_secret}:{battle.id}:{user.id}".encode()).hexdigest()
    picked = random.Random(seed).sample(rules.SHOT_RANDOM_POOL, rules.SHOT_RANDOM_COUNT)
    fixed = list(rules.SHOT_FIXED)
    # 화면 순서: 첫 고정 구도(대표 사진) → 랜덤 구도 → 나머지 고정 구도(키워드 인증샷은 마지막)
    return fixed[:1] + picked + fixed[1:]


def shot_label(key: str) -> str:
    return rules.SHOT_TYPES.get(key, {}).get("label", key)


def shot_guide(battle: Battle, user: User) -> list:
    return [
        {"order": i + 1, "shot_type": k, "label": shot_label(k), "guide": rules.SHOT_TYPES[k]["guide"],
         "is_random": k not in rules.SHOT_FIXED}
        for i, k in enumerate(required_shots(battle, user))
    ]
