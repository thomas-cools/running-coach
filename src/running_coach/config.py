from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RUNNING_COACH_")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    supabase_url: HttpUrl | None = None
    supabase_anon_key: str | None = None
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    max_sample_count: int = Field(default=100_000, gt=0)
    max_activity_duration_seconds: int = Field(default=24 * 60 * 60, gt=0)
    parse_timeout_seconds: float = Field(default=20.0, gt=0)

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return f"postgresql+psycopg://{value.removeprefix('postgresql://')}"
        if value.startswith("postgres://"):
            return f"postgresql+psycopg://{value.removeprefix('postgres://')}"
        return value
