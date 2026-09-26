import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import rules
from ..auth import create_access_token, dummy_verify, get_current_user, hash_password, verify_password
from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, SignupRequest, TokenResponse
from ..services import ratelimit
from ..services.accounts import validate_nickname
from ..services.friends import make_friends
from ..services.points import award
from ..services.serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _new_invite_code(db: Session) -> str:
    while True:
        code = secrets.token_hex(4).upper()  # 8자리 (추측하기 어렵게)
        if not db.query(User).filter(User.invite_code == code).first():
            return code


@router.get("/check-email")
def check_email(email: str, request: Request, db: Session = Depends(get_db)):
    """이메일 중복 확인 (가입 화면용)."""
    ratelimit.hit(f"check:{_client_ip(request)}", 60, 60, "요청이 너무 많아요")
    e = email.strip().lower()[:254]
    return {"email": e, "available": db.query(User).filter(User.email == e).first() is None}


@router.get("/check-nickname")
def check_nickname(nickname: str, request: Request, db: Session = Depends(get_db)):
    """닉네임 확인: 형식·금지어·중복을 모두 검사해 사용 가능 여부와 이유를 알려준다."""
    ratelimit.hit(f"check:{_client_ip(request)}", 60, 60, "요청이 너무 많아요")
    n = nickname.strip()[:30]
    try:
        validate_nickname(db, n)
        return {"nickname": n, "available": True, "reason": None}
    except HTTPException as e:
        return {"nickname": n, "available": False, "reason": e.detail}


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    """이메일+비밀번호로 계정을 만들고, 닉네임(중복 불가)과 요리 실력을 함께 설정."""
    ratelimit.hit(f"signup:{_client_ip(request)}", 30, 3600, "가입 시도가 너무 많아요")
    email = payload.email.lower()
    if payload.skill not in rules.SKILLS:
        raise HTTPException(status_code=400, detail="요리 실력(상/중/하)을 선택해 주세요")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")
    nickname = validate_nickname(db, payload.nickname, email=email)

    inviter = None
    if payload.invite_code:
        inviter = db.query(User).filter(User.invite_code == payload.invite_code.strip().upper()[:16]).first()
        if inviter is None:
            raise HTTPException(status_code=400, detail="존재하지 않는 초대 코드입니다")

    user = User(
        email=email,
        nickname=nickname,
        password_hash=hash_password(payload.password),
        skill=payload.skill,
        total_points=0,
        points=0,
        is_admin=email in settings.admin_email_set,
        invite_code=_new_invite_code(db),
        invited_by_id=inviter.id if inviter else None,
    )
    try:
        db.add(user)
        db.flush()
        if inviter:
            award(db, inviter, rules.INVITE_POINTS_INVITER, "invite", f"user:{user.id}", memo=f"{nickname}님 초대")
            award(db, user, rules.INVITE_POINTS_INVITEE, "invited", f"user:{inviter.id}",
                  memo=f"{inviter.nickname}님 초대로 가입")
            if rules.INVITE_AUTO_FRIEND:
                make_friends(db, inviter, user)
        db.commit()
    except IntegrityError:  # 같은 이메일/닉네임으로 동시에 가입한 경우
        db.rollback()
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일 또는 닉네임입니다")
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=user_out(user))


def _authenticate(db: Session, email: str, password: str, ip: str) -> User:
    email = email.strip().lower()
    # 같은 이메일 10회/10분, 같은 IP 30회/10분 → 비밀번호 무차별 대입 방지
    ratelimit.hit(f"login:{email}", 10, 600, "로그인 시도가 너무 많아요")
    ratelimit.hit(f"login-ip:{ip}", 30, 600, "로그인 시도가 너무 많아요")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        dummy_verify()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다")
    ratelimit.reset(f"login:{email}")  # 성공하면 해당 이메일 카운트 초기화
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = _authenticate(db, payload.email, payload.password, _client_ip(request))
    return TokenResponse(access_token=create_access_token(user), user=user_out(user))


@router.post("/token", include_in_schema=False)
def token_for_swagger(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Swagger Authorize 버튼 전용. username 칸에 이메일 입력."""
    user = _authenticate(db, form.username, form.password, _client_ip(request))
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.post("/logout-all")
def logout_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """모든 기기에서 로그아웃 (지금까지 발급된 토큰 전부 무효). 폰을 잃어버렸을 때 등."""
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    return {"status": "ok", "message": "모든 기기에서 로그아웃했어요. 다시 로그인해 주세요"}
