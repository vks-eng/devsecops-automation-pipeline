"""Application configuration loaded from environment variables (12-factor)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AdapterMode = Literal["mock", "real"]
TrivyMode = Literal["mock", "binary", "docker"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DevSecOps Automation Platform"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"

    # --- Database (PostgreSQL only) -------------------------------------------------
    database_url: str = "postgresql+psycopg2://devsecops:devsecops@localhost:5432/devsecops"

    # --- Auth -------------------------------------------------------------------------
    secret_key: str = Field(default="change-me-in-production-please-32b+", min_length=16)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 60
    allow_registration: bool = True

    # Fernet key (urlsafe base64, 32 bytes) for encrypting integration tokens at rest.
    # If empty, a key is derived from SECRET_KEY (acceptable for dev only).
    token_encryption_key: str = ""

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    # --- Background processing --------------------------------------------------------
    # eager=True executes Celery tasks in-process (no Redis needed). Default for dev/test.
    celery_task_always_eager: bool = True
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- Integration adapters (mock is default: no credentials needed) ----------------
    github_mode: AdapterMode = "mock"
    github_api_url: str = "https://api.github.com"
    github_webhook_secret: str = ""
    sonarqube_mode: AdapterMode = "mock"
    sonarqube_url: str = "http://localhost:9000"
    sonarqube_token: str = ""
    trivy_mode: TrivyMode = "mock"
    trivy_binary: str = "trivy"
    trivy_docker_image: str = "aquasec/trivy:0.58.1"
    trivy_timeout_seconds: int = 600
    docker_mode: AdapterMode = "mock"
    docker_binary: str = "docker"
    pip_audit_mode: AdapterMode = "mock"
    pip_audit_binary: str = "pip-audit"
    pip_audit_timeout_seconds: int = 300
    http_timeout_seconds: float = 15.0

    # --- Notifications ----------------------------------------------------------------
    notification_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "devsecops@localhost"
    smtp_use_tls: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip().startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("database_url")
    @classmethod
    def _postgres_only(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("Only PostgreSQL database URLs are supported")
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
