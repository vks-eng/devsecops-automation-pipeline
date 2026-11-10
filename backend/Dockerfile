# syntax=docker/dockerfile:1.7
# Multi-stage build for the ShieldOps API and worker. Both run as a non-root user.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG TRIVY_IMAGE=aquasec/trivy:0.58.1

# ---------------------------------------------------------------- builder
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools && pip install -r requirements.txt
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-deps .

# ---------------------------------------------------------------- api runtime
FROM ${PYTHON_IMAGE} AS api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
RUN groupadd --system --gid 10001 shieldops \
    && useradd --system --uid 10001 --gid shieldops --home-dir /app --shell /usr/sbin/nologin shieldops
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=shieldops:shieldops alembic.ini ./
COPY --chown=shieldops:shieldops alembic ./alembic
COPY --chown=shieldops:shieldops app ./app
USER shieldops
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4); sys.exit(0)"
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]

# ---------------------------------------------------------------- worker runtime (adds Trivy + pip-audit)
FROM ${TRIVY_IMAGE} AS trivy

FROM api AS worker
USER root
COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
RUN /opt/venv/bin/pip install --no-cache-dir "pip-audit>=2.7"
USER shieldops
HEALTHCHECK NONE
CMD ["celery", "-A", "app.worker.celery_app", "worker", "-B", "--loglevel=INFO", "--concurrency=2", "--schedule=/tmp/celerybeat-schedule"]
