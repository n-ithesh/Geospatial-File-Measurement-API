"""Application configuration via pydantic-settings.

All settings can be overridden by environment variables (case-insensitive).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./geospatial.db",
        description="SQLAlchemy database URL. Supports SQLite and PostgreSQL.",
    )

    # Storage
    STORAGE_DIR: Path = Field(
        default=Path("./uploads"),
        description="Directory where uploaded files are stored.",
    )

    # Upload limits
    MAX_UPLOAD_MB: int = Field(
        default=50,
        ge=1,
        description="Maximum upload file size in megabytes.",
    )
    MAX_UNCOMPRESSED_MB: int = Field(
        default=200,
        ge=1,
        description="Maximum total uncompressed size for zip archives in megabytes.",
    )

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins.",
    )

    # App meta
    APP_NAME: str = "Geospatial File Measurement API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    @field_validator("STORAGE_DIR", mode="before")
    @classmethod
    def coerce_storage_dir(cls, v: object) -> Path:
        """Coerce string paths to Path objects."""
        return Path(str(v))

    @property
    def max_upload_bytes(self) -> int:
        """Return MAX_UPLOAD_MB in bytes."""
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def max_uncompressed_bytes(self) -> int:
        """Return MAX_UNCOMPRESSED_MB in bytes."""
        return self.MAX_UNCOMPRESSED_MB * 1024 * 1024


settings = Settings()
