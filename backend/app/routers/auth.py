from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import GoogleAuthRequest, LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        skill_tier=payload.skill_tier,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.post("/google", response_model=TokenResponse)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="Google 로그인이 서버에 설정되지 않았습니다")

    try:
        claims = google_id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 Google 토큰입니다")

    google_sub = claims["sub"]
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google 계정에서 이메일을 가져올 수 없습니다")

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user is None:
        # Not linked yet — fall back to matching by email so someone who
        # signed up with email/password first can still use "구글로 로그인".
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            user.google_sub = google_sub
        else:
            if payload.skill_tier is None:
                raise HTTPException(
                    status_code=400, detail="처음 가입하는 계정입니다. skill_tier를 함께 보내주세요"
                )
            user = User(
                email=email,
                google_sub=google_sub,
                nickname=claims.get("name") or email.split("@")[0],
                skill_tier=payload.skill_tier,
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user)
