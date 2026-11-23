from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Campus Book Loop"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./campus_book_loop.db"
    token_secret: str = "local-development-secret-change-me"
    token_expire_minutes: int = 240
    cors_origins: str = "http://localhost:3000"
    seed_on_startup: bool = True
    # Local development and tests may create tables directly. Deployed
    # environments run `alembic upgrade head` and set this to false.
    auto_create_schema: bool = True
    model_dir: str = "app/resources"
    # Listing images are stored on the API host and served from /media.
    upload_dir: str = "uploads"
    media_url_prefix: str = "/media"
    max_image_bytes: int = 5 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

_WEAK_TOKEN_SECRETS = frozenset(
    {
        "local-development-secret-change-me",
        "change-me-in-local-environment",
        "change-me",
        "test-secret",
    }
)


def validate_production_settings() -> None:
    """Refuse to start production with a weak or default signing secret."""
    if settings.app_env != "production":
        return
    if len(settings.token_secret) < 32 or settings.token_secret in _WEAK_TOKEN_SECRETS:
        raise RuntimeError(
            "TOKEN_SECRET must be a random value of at least 32 characters "
            "when APP_ENV=production"
        )
