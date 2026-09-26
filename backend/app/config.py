import logging
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DEFAULT_SECRET = "change-this-secret-in-production"
log = logging.getLogger("cookbattle")


class Settings(BaseSettings):
    # extra="ignore": .env에 예전 버전 항목(ADMIN_NICKNAMES 등)이 남아 있어도 서버가 죽지 않게
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    database_url: str = "sqlite:///./cookbattle.db"
    jwt_secret: str = DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days
    upload_dir: str = "./uploads"
    timezone: str = "Asia/Seoul"
    admin_emails: str = ""  # comma separated. 이 이메일로 가입하면 관리자
    cors_origins: str = "*"  # 배포 시 프론트 주소로 제한 (예: https://cookbattle.vercel.app)
    max_request_mb: int = 30  # 요청 본문 최대 크기

    # 이미지 인식 AI (Claude Vision). 키가 없으면 AI 검사는 건너뛴다.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ai_check_mode: str = "strict"  # off | advisory(기록만) | strict(문제 있으면 거절)

    @property
    def admin_email_set(self) -> set:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def cors_origin_list(self) -> list:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]


def _resolve_paths(s: Settings) -> None:
    """상대 경로를 backend 폴더 기준으로 고정 → 어느 폴더에서 실행해도 같은 DB·업로드 폴더를 쓴다."""
    prefix = "sqlite:///"
    if s.database_url.startswith(prefix) and not s.database_url.startswith(prefix + "/"):
        rel = s.database_url[len(prefix):]
        if not Path(rel).is_absolute():
            s.database_url = prefix + str((BASE_DIR / rel).resolve())
    if not Path(s.upload_dir).is_absolute():
        s.upload_dir = str((BASE_DIR / s.upload_dir).resolve())


def _ensure_secret(s: Settings) -> None:
    """JWT 비밀키가 기본값이면 누구나 관리자 토큰을 위조할 수 있다.
    → backend/.jwt_secret 파일에 랜덤 키를 만들어 두고 사용 (git에 올라가지 않음)."""
    if s.jwt_secret != DEFAULT_SECRET and len(s.jwt_secret) >= 16:
        return
    key_file = BASE_DIR / ".jwt_secret"
    try:
        if not key_file.exists():
            key_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        s.jwt_secret = key_file.read_text(encoding="utf-8").strip()
    except OSError:
        s.jwt_secret = secrets.token_urlsafe(48)  # 파일을 못 쓰면 실행할 때마다 새 키 (재시작 시 재로그인)
    log.warning("JWT_SECRET이 설정되지 않아 backend/.jwt_secret 의 랜덤 키를 사용합니다.")


settings = Settings()
_resolve_paths(settings)
_ensure_secret(settings)
