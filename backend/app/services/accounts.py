"""닉네임 규칙 (가입·닉네임 변경 공통)."""
import re
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User

NICKNAME_RE = re.compile(r"^[가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9_]{2,12}$")
# 운영진 사칭 방지: 이 단어가 들어간 닉네임은 관리자 이메일만 사용 가능
RESERVED_WORDS = ("관리자", "운영자", "운영진", "admin", "쿡배틀", "cookbattle", "system", "시스템")


def validate_nickname(db: Session, nickname: str, email: Optional[str] = None,
                      exclude_user_id: Optional[int] = None) -> str:
    n = nickname.strip()
    if not NICKNAME_RE.match(n):
        raise HTTPException(status_code=400, detail="닉네임은 2~12자의 한글·영문·숫자·_ 만 쓸 수 있어요")
    is_admin_email = email is not None and email.lower() in settings.admin_email_set
    if not is_admin_email and any(w in n.lower() for w in RESERVED_WORDS):
        raise HTTPException(status_code=400, detail="사용할 수 없는 닉네임이에요")
    q = db.query(User).filter(User.nickname == n)
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    if q.first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다")
    return n
