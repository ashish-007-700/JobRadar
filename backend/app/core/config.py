from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session_name: str = "jobradar"

    supabase_url: str | None = None
    supabase_key: str | None = None

    cors_origins: str = "http://localhost:5173"
    max_resolution_depth: int = 5

    @field_validator("telegram_api_id", "telegram_api_hash", "supabase_url", "supabase_key", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        return None if value == "" else value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
