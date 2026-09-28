"""Checks a battle entry's two submission photos with a vision model: do they show the same
dish, and does the second one actually match the battle's randomly-assigned required angle?
This is the main defense against submitting a photo lifted from the internet — a stolen photo
can't be re-shot to order from whatever angle a given battle happens to ask for.

If ANTHROPIC_API_KEY isn't configured (local dev/demo), the check is skipped and always passes —
the same fallback shape as services.email when SMTP isn't configured."""
import base64
import json
import logging
from typing import Tuple

from ..config import settings

log = logging.getLogger("cookbattle")

_MEDIA_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def check_angle_photos(front: bytes, front_ext: str, angle: bytes, angle_ext: str, angle_label: str) -> Tuple[bool, str]:
    """Returns (ok, reason); reason is a short Korean sentence to show the user when ok is False."""
    if not settings.anthropic_api_key:
        log.warning("ANTHROPIC_API_KEY not set — skipping angle-photo verification.")
        return True, ""

    import anthropic  # imported lazily so the dependency is only needed when a key is configured

    prompt = (
        "요리 대결 참가 인증 사진 두 장을 심사해줘. 첫 번째는 기본(정면) 사진, 두 번째는 "
        f"'{angle_label}' 구도로 찍었다고 주장하는 추가 사진이야. 다음 JSON 형식으로만 답해, 다른 말은 하지 마:\n"
        '{"same_dish": true 또는 false, "matches_angle": true 또는 false, "reason": "한국어 한 문장"}\n'
        "same_dish는 두 사진이 같은 음식/같은 그릇을 찍은 게 맞는지, "
        f"matches_angle은 두 번째 사진이 실제로 '{angle_label}' 구도에 맞는지를 판정해."
    )
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.angle_check_model,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": _MEDIA_TYPES[front_ext], "data": base64.b64encode(front).decode()},
                        },
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": _MEDIA_TYPES[angle_ext], "data": base64.b64encode(angle).decode()},
                        },
                    ],
                }
            ],
        )
        text = resp.content[0].text
        verdict = json.loads(text[text.index("{") : text.rindex("}") + 1])
    except Exception:
        # A flaky external API shouldn't block a real submission — fail open, same as an unset key.
        log.exception("angle-photo verification call failed; passing the submission through")
        return True, ""

    if not verdict.get("same_dish", True):
        return False, "두 사진이 같은 음식으로 안 보여요. 다시 찍어주세요"
    if not verdict.get("matches_angle", True):
        return False, verdict.get("reason") or f"두 번째 사진이 요청한 구도({angle_label})와 달라요. 다시 찍어주세요"
    return True, ""
