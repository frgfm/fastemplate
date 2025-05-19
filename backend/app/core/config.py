# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import os
import secrets
import socket
from typing import Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["settings"]


class Settings(BaseSettings):
    # State
    PROJECT_NAME: str = "Fastemplate API"
    PROJECT_DESCRIPTION: str = "Template backend API for FastAPI projects"
    VERSION: str = "0.1.0.dev0"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGIN: str = "*"
    SUPPORT_EMAIL: str = os.environ.get("SUPPORT_EMAIL", "support@email.com")
    # Superadmin
    SUPERADMIN_EMAIL: str = os.environ["SUPERADMIN_EMAIL"]
    SUPERADMIN_PWD: str = os.environ["SUPERADMIN_PWD"]
    # Services
    RESEND_KEY: str = os.environ["RESEND_KEY"]
    EMAIL_FROM: str = os.environ["EMAIL_FROM"]
    BACKEND_HOST: str = os.environ["BACKEND_HOST"]
    RESEND_VERIFY_API_KEY: bool = os.environ.get("RESEND_VERIFY_API_KEY", "true").lower() == "true"
    # DB
    POSTGRES_URL: str = os.environ["POSTGRES_URL"]
    POSTGRES_MAX_POOL_SIZE: int = int(os.environ.get("POSTGRES_MAX_POOL_SIZE", 10))
    POSTGRES_MAX_OVERFLOW: int = int(os.environ.get("POSTGRES_MAX_OVERFLOW", 20))

    @field_validator("POSTGRES_URL")
    @classmethod
    def sqlachmey_uri(cls, v: str) -> str:
        # Fix for SqlAlchemy 1.4+
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # Security
    JWT_SECRET: str = os.environ.get("JWT_SECRET", secrets.token_urlsafe(32))
    JWT_EXPIRE_MINUTES: int = 60
    JWT_UNLIMITED: int = 60 * 24 * 365
    JWT_ALGORITHM: str = "HS256"

    # Storage
    S3_ACCESS_KEY: str = os.environ["S3_ACCESS_KEY"]
    S3_SECRET_KEY: str = os.environ["S3_SECRET_KEY"]
    S3_REGION: str = os.environ["S3_REGION"]
    S3_ENDPOINT_URL: str = os.environ["S3_ENDPOINT_URL"]
    S3_BUCKET_NAME: str = os.environ.get("S3_BUCKET_NAME", "fastemplate")
    S3_PROXY_URL: str = os.environ.get("S3_PROXY_URL", "")
    S3_URL_EXPIRATION: int = int(os.environ.get("S3_URL_EXPIRATION") or 24 * 3600)

    # Error monitoring
    SENTRY_DSN: Union[str, None] = os.environ.get("SENTRY_DSN")
    SERVER_NAME: str = os.environ.get("SERVER_NAME", socket.gethostname())

    @field_validator("SENTRY_DSN")
    @classmethod
    def sentry_dsn_can_be_blank(cls, v: str) -> Union[str, None]:
        if not isinstance(v, str) or len(v) == 0:
            return None
        return v

    # Logs & APM
    LOGFIRE_TOKEN: str | None = os.environ.get("LOGFIRE_TOKEN")

    # Product analytics
    POSTHOG_KEY: str | None = os.environ.get("POSTHOG_KEY")

    DEBUG: bool = os.environ.get("DEBUG", "").lower() != "false"
    LOGO_URL: str = ""

    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
