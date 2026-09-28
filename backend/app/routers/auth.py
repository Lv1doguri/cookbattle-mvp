import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Query
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import clock
from ..config import settings
from ..content import EMAIL_VERIFICATION_TTL, SIGNUP_BONUS
from ..database import get_db
from ..enums import Tier
from ..errors import ApiError
from ..models import PendingSignup, User
from ..schemas import (
    AuthOut,
    GoogleAuthIn,
    LoginIn,
    NicknameAvailableOut,
    ResendVerificationIn,
    SignupIn,
    SignupPendingOut,
    VerifyEmailIn,
)
from ..security import create_access_token, hash_password, verify_password
from ..services import throttle
from ..services.accounts import build_me, nickname_taken
from ..services.email import send_verification_email
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


def _purge_expired_pending(db: Session, now) -> None:
    db.execute(delete(PendingSignup).where(PendingSignup.expires_at <= now))


def _create_and_send_verification(db: Session, email: str, nickname: str, password_hash: str, tier: Tier, now) -> None:
    token = secrets.token_urlsafe(32)
    db.add(
        PendingSignup(
            email=email, nickname=nickname, password_hash=password_hash, tier=tier,
            token=token, created_at=now, expires_at=now + EMAIL_VERIFICATION_TTL,
        )
    )
    db.commit()
    send_verification_email(email, nickname, token)


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


@router.post("/signup", response_model=SignupPendingOut, status_code=202)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    """회원가입 화면의 [가입하기]. 계정은 바로 만들어지지 않아요 — 입력한 이메일로 인증 메일을 보내고,
    그 안의 링크를 눌러야(`POST /auth/verify-email`) 실제 계정이 생기고 로그인 상태가 돼요."""
    now = clock.utcnow()
    email = body.email.strip().lower()
    _purge_expired_pending(db, now)

    if nickname_taken(db, body.nickname):
        raise NICKNAME_TAKEN
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EMAIL_TAKEN
    if db.scalar(select(PendingSignup.id).where(PendingSignup.email == email, PendingSignup.expires_at > now)) is not None:
        raise ApiError(409, "verification_already_sent", "이미 이 이메일로 인증 메일을 보냈어요. 메일함을 확인해주세요")

    try:
        _create_and_send_verification(db, email, body.nickname, hash_password(body.password), body.tier, now)
    except IntegrityError:  # lost a race on email
        db.rollback()
        raise EMAIL_TAKEN
    return SignupPendingOut(message="인증 메일을 보냈어요. 메일함을 확인하고 링크를 눌러 가입을 완료해주세요", email=email)


@router.post("/verify-email", response_model=AuthOut)
def verify_email(body: VerifyEmailIn, db: Session = Depends(get_db)):
    """메일의 인증 링크를 누르면 프론트가 이 API를 불러요. 성공하면 계정이 만들어지고 바로 로그인돼요."""
    now = clock.utcnow()
    pending = db.scalar(select(PendingSignup).where(PendingSignup.token == body.token))
    if pending is None or pending.expires_at <= now:
        raise ApiError(400, "invalid_or_expired_token", "인증 링크가 잘못됐거나 만료됐어요. 다시 가입해주세요")

    email, nickname, password_hash, tier = pending.email, pending.nickname, pending.password_hash, pending.tier
    db.delete(pending)
    db.commit()

    # Re-check now that our own reservation is gone: someone else may have taken the nickname/email
    # while this one sat unverified (nickname_taken() would otherwise always match the row itself).
    if nickname_taken(db, nickname):
        raise NICKNAME_TAKEN
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EMAIL_TAKEN

    user = User(email=email, password_hash=password_hash, nickname=nickname, tier=tier, is_admin=_is_admin_email(email))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise NICKNAME_TAKEN if nickname_taken(db, nickname) else EMAIL_TAKEN
    grant_points(db, user, SIGNUP_BONUS, reason="signup", ref_type="user", ref_id=user.id)
    db.commit()
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))


@router.post("/resend-verification", response_model=SignupPendingOut)
def resend_verification(body: ResendVerificationIn, db: Session = Depends(get_db)):
    """인증 메일을 다시 보내요 (10분에 10번까지)."""
    now = clock.utcnow()
    email = body.email.strip().lower()
    throttle.check(f"resend:{email}")
    throttle.record_failure(f"resend:{email}")

    _purge_expired_pending(db, now)
    pending = db.scalar(select(PendingSignup).where(PendingSignup.email == email))
    if pending is None:
        # 계정 존재 여부를 흘리지 않되, 보낸 사람 입장에서는 같은 메시지로 보여요.
        return SignupPendingOut(message="인증 메일을 보냈어요. 메일함을 확인하고 링크를 눌러 가입을 완료해주세요", email=email)

    pending.token = secrets.token_urlsafe(32)
    pending.expires_at = now + EMAIL_VERIFICATION_TTL
    db.commit()
    send_verification_email(pending.email, pending.nickname, pending.token)
    return SignupPendingOut(message="인증 메일을 다시 보냈어요. 메일함을 확인해주세요", email=email)


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
        if user is None and "@" in who and db.scalar(select(PendingSignup.id).where(PendingSignup.email == who)):
            raise ApiError(403, "email_not_verified", "이메일 인증을 아직 완료하지 않았어요. 메일함을 확인해주세요")
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
