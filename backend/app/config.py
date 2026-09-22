from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./cookbattle.db"
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days, convenient for a hackathon demo
    upload_dir: str = "./uploads"

    class Config:
        env_file = ".env"


settings = Settings()
