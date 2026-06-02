from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AnoChat Workspace"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/anochat"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    upload_dir: Path = Path("../uploads")
    max_upload_bytes: int = 25 * 1024 * 1024
    allowed_upload_types: str = (
        "image/jpeg,image/png,image/gif,image/" + "webp,image/svg+xml,"
        "application/pdf,text/plain,text/csv,"
        "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "audio/mpeg,audio/ogg,audio/wav,audio/" + "webm,audio/mp4,"
        "video/mp4,video/" + "webm,video/ogg"
    )
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173"
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "Admin123!"
    seed_customer_email: str = "customer@example.com"
    seed_customer_password: str = "Customer123!"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def allowed_upload_type_set(self) -> set[str]:
        return {item.strip() for item in self.allowed_upload_types.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
