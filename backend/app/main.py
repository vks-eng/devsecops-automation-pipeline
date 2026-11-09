"""FastAPI application factory for ShieldOps."""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    dashboard,
    notifications,
    pipelines,
    projects,
    reports,
    scans,
    system,
    webhooks,
)
from app.core.config import get_settings
from app.core.logging import configure_logging

DESCRIPTION = (
    "ShieldOps automates code-quality checks, security scanning, container scanning and "
    "CI/CD pipeline reporting, with a centralised dashboard of each project's security "
    "posture. Integrations (GitHub Actions, SonarQube, Trivy, Docker, pip-audit) run in "
    "mock mode by default."
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="ShieldOps: DevSecOps Automation Platform",
        version="1.0.0",
        description=DESCRIPTION,
        license_info={"name": "MIT"},
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if not request.url.path.endswith("/docs"):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
            )
        return response

    for module in (
        system,
        auth,
        projects,
        scans,
        pipelines,
        dashboard,
        reports,
        notifications,
        webhooks,
    ):
        app.include_router(module.router, prefix=settings.api_prefix)
    return app


app = create_app()
