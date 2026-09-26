"""이미 가입한 계정에 관리자 권한 주기/빼기 (서버 컴퓨터에서만 실행 가능 → 가장 안전한 방법).

사용법 (backend 폴더에서):
    python -m app.make_admin a@test.com           # 관리자로 지정
    python -m app.make_admin a@test.com --remove  # 관리자 해제
"""
import sys

from .database import Base, SessionLocal, engine, migrate_sqlite
from .models import User


def main(argv: list) -> int:
    if not argv:
        print(__doc__)
        return 1
    email, remove = argv[0].strip().lower(), "--remove" in argv[1:]
    Base.metadata.create_all(bind=engine)
    migrate_sqlite()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"'{email}' 계정을 찾을 수 없어요. 먼저 회원가입하세요.")
            return 1
        user.is_admin = not remove
        user.token_version = (user.token_version or 0) + 1  # 권한이 바뀌었으니 다시 로그인하게
        db.commit()
        print(f"{user.nickname}({email}) → {'관리자 해제' if remove else '관리자 지정'} 완료. 다시 로그인하세요.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
