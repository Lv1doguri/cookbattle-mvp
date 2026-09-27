import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Query
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..content import SIGNUP_BONUS
from ..database import get_db
from ..enums import Tier
from ..errors import ApiError
from ..models import User
from ..schemas import AuthOut, GoogleAuthIn, LoginIn, NicknameAvailableOut, SignupIn
from ..security import create_access_token, hash_password, verify_password
from ..services import throttle
from ..services.accounts import build_me, nickname_taken
from ..services.points import grant_points

router = APIRouter(prefix="/auth", tags=["auth"])


def _is_admin_email(email: Optional[str]) -> bool:
    admin_emails = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}
    return bool(email) and email.lower() in admin_emails

# Verified against when the email is unknown, so "no such user" and "wrong password" take equally long.
_DUMMY_HASH = hash_password("not-a-real-password")

NICKNAME_TAKEN = ApiError(409, "nickname_taken", "이미 사용 중인 닉네임입니다")
EMAIL_TAKEN = ApiError(409, "email_taken", "이미 가입된 이메일입니다")
GOOGLE_SIGNUP_DEFAULT_TIER = Tier.beginner  # 구글 가입엔 실력 선택 화면이 없어요 — API_CONTRACT.md 참고


def _unique_nickname(db: Session, seed: str) -> str:
    """구글 표시 이름을 그대로 쓰되, 겹치면(또는 형식이 안 맞으면) 랜덤 접미사를 붙여요."""
    base = "".join(ch for ch in seed if ch.isalnum())[:12]
    if len(base) < 2:
        base = "요리사"
    candidate = base
    for _ in range(20):
        if not nickname_taken(db, candidate):
            return candidate
        candidate = f"{base}{secrets.randbelow(9000) + 1000}"
    raise ApiError(500, "nickname_generation_failed", "잠시 후 다시 시도해주세요")


@router.get("/nickname-available", response_model=NicknameAvailableOut)
def nickname_available(
    nickname: str = Query(min_length=2, max_length=16),
    db: Session = Depends(get_db),
):
    """회원가입 화면에서 닉네임을 입력하며(또는 포커스를 잃을 때) 중복 확인용으로 부르세요."""
    return NicknameAvailableOut(available=not nickname_taken(db, nickname))


@router.post("/signup", response_model=AuthOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    """회원가입 화면의 [가입하기]. 가입하면 바로 로그인된 상태(토큰)로 돌아와요. 이메일은 선택이에요."""
    email = body.email.strip().lower() if body.email else None
    if nickname_taken(db, body.nickname):
        raise NICKNAME_TAKEN
    if email is not None and db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EMAIL_TAKEN

    user = User(
        email=email, password_hash=hash_password(body.password), nickname=body.nickname, tier=body.tier,
        is_admin=_is_admin_email(email),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # lost a race on nickname or email; report whichever is now taken
        db.rollback()
        raise NICKNAME_TAKEN if nickname_taken(db, body.nickname) else EMAIL_TAKEN
    grant_points(db, user, SIGNUP_BONUS, reason="signup", ref_type="user", ref_id=user.id)
    db.commit()
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    """로그인. `email`에 이메일을 넣어요. 이메일 없이 가입한 계정은 같은 칸에 닉네임을 넣으면 돼요."""
    who = body.email.strip().lower()
    throttle.check(who)
    if "@" in who:
        user = db.scalar(select(User).where(User.email == who))
    else:
        user = db.scalar(select(User).where(func.lower(User.nickname) == who))
    ok = verify_password(body.password, user.password_hash if user and user.password_hash else _DUMMY_HASH)
    if user is None or not ok:
        throttle.record_failure(who)
        raise ApiError(401, "invalid_credentials", "이메일 또는 비밀번호가 올바르지 않습니다")
    throttle.reset(who)
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))


@router.post("/google", response_model=AuthOut)
def google_auth(body: GoogleAuthIn, db: Session = Depends(get_db)):
    """로그인/회원가입 화면의 [Google로 계속하기]. 프론트가 Google Identity Services로 받은
    ID 토큰을 그대로 보내면, 서버가 구글에 검증하고 계정을 찾거나 새로 만들어요."""
    if not settings.google_client_id:
        raise ApiError(500, "google_not_configured", "Google 로그인이 서버에 설정되지 않았어요")
    try:
        claims = google_id_token.verify_oauth2_token(
            body.id_token, google_requests.Request(), settings.google_client_id
        )
    except ValueError:
        raise ApiError(401, "invalid_google_token", "유효하지 않은 Google 토큰이에요")

    google_sub = claims["sub"]
    email = claims.get("email")
    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is None and email:
        # 이메일/비밀번호로 먼저 가입한 계정과 같은 이메일이면 그 계정에 구글 로그인을 연결해요.
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is not None:
            user.google_sub = google_sub
            db.commit()
    if user is None:
        nickname = _unique_nickname(db, claims.get("name") or (email or "요리사").split("@")[0])
        user = User(
            email=email.lower() if email else None,
            google_sub=google_sub,
            nickname=nickname,
            tier=body.tier or GOOGLE_SIGNUP_DEFAULT_TIER,
            is_admin=_is_admin_email(email),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ApiError(409, "email_taken", "이미 가입된 이메일입니다")
        grant_points(db, user, SIGNUP_BONUS, reason="signup", ref_type="user", ref_id=user.id)
        db.commit()
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))
