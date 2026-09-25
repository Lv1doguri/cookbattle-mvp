import re
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ApiError
from ..models import User
from ..schemas import AuthOut, LoginIn, SignupIn
from ..security import create_access_token, hash_password, verify_password
from ..services.serialize import build_me

router = APIRouter(prefix="/auth", tags=["auth"])

_NON_HANDLE = re.compile(r"[^a-z0-9_]")
# Verified against when the email is unknown, so "no such user" and "wrong password" take equally long.
_DUMMY_HASH = hash_password("not-a-real-password")


def _make_handle(db: Session, *seeds: str) -> str:
    base = ""
    for seed in seeds:
        base = _NON_HANDLE.sub("", seed.lower())[:14]
        if len(base) >= 3:
            break
    if len(base) < 3:
        base = "cook"
    candidate = base
    for _ in range(30):
        if db.scalar(select(User.id).where(User.handle == candidate)) is None:
            return candidate
        candidate = f"{base}{secrets.randbelow(9000) + 1000}"
    raise ApiError(500, "handle_generation_failed", "잠시 후 다시 시도해주세요")


@router.post("/signup", response_model=AuthOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    local_part = email.split("@")[0]
    nickname = body.nickname or local_part[:30]

    for _attempt in range(3):
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise ApiError(409, "email_taken", "이미 가입된 이메일입니다")
        user = User(
            email=email,
            password_hash=hash_password(body.password),
            nickname=nickname,
            handle=_make_handle(db, nickname, local_part),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # lost a race on email or handle; the loop re-checks which
            db.rollback()
            continue
        return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))
    raise ApiError(409, "email_taken", "이미 가입된 이메일입니다")


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok:
        raise ApiError(401, "invalid_credentials", "이메일 또는 비밀번호가 올바르지 않습니다")
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))
