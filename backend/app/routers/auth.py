from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ApiError
from ..models import User
from ..schemas import AuthOut, LoginIn, NicknameAvailableOut, SignupIn
from ..security import create_access_token, hash_password, verify_password
from ..services.accounts import build_me, nickname_taken

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the email is unknown, so "no such user" and "wrong password" take equally long.
_DUMMY_HASH = hash_password("not-a-real-password")

NICKNAME_TAKEN = ApiError(409, "nickname_taken", "이미 사용 중인 닉네임입니다")
EMAIL_TAKEN = ApiError(409, "email_taken", "이미 가입된 이메일입니다")


@router.get("/nickname-available", response_model=NicknameAvailableOut)
def nickname_available(
    nickname: str = Query(min_length=2, max_length=16),
    db: Session = Depends(get_db),
):
    """회원가입 화면에서 닉네임을 입력하며(또는 포커스를 잃을 때) 중복 확인용으로 부르세요."""
    return NicknameAvailableOut(available=not nickname_taken(db, nickname))


@router.post("/signup", response_model=AuthOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if nickname_taken(db, body.nickname):
        raise NICKNAME_TAKEN
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EMAIL_TAKEN

    user = User(email=email, password_hash=hash_password(body.password), nickname=body.nickname, tier=body.tier)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # lost a race on nickname or email; report whichever is now taken
        db.rollback()
        raise NICKNAME_TAKEN if nickname_taken(db, body.nickname) else EMAIL_TAKEN
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok:
        raise ApiError(401, "invalid_credentials", "이메일 또는 비밀번호가 올바르지 않습니다")
    return AuthOut(access_token=create_access_token(user.id), user=build_me(db, user))
