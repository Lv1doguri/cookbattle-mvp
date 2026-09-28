from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./cookbattle.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 8 * 1024 * 1024
    cors_origins: str = "*"
    google_client_id: str = ""
    admin_emails: str = ""  # comma-separated; these accounts get is_admin=True on signup

    # Vision model that checks the second (angle) submission photo. If empty, the check is
    # skipped and every submission passes — same local-dev fallback shape as SMTP above.
    anthropic_api_key: str = ""
    angle_check_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
