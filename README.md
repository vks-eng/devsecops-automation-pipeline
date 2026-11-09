# ShieldOps: DevSecOps Automation Platform

**One dashboard for code quality, dependency, container and CI/CD security across all your projects, with scanners wired in behind safe, swappable adapters.**

[![CI](https://github.com/vks-eng/devsecops-automation-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/vks-eng/devsecops-automation-pipeline/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Trivy](https://img.shields.io/badge/Trivy-container%20scanning-1904DA?logo=aqua&logoColor=white)
![SonarQube](https://img.shields.io/badge/SonarQube-code%20quality-4E9BCD?logo=sonarqube&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

ShieldOps registers your GitHub repositories, pulls CI/CD history from GitHub Actions, runs
**SonarQube**, **Trivy** and **pip-audit** analyses through isolated adapters, normalises every
finding into one severity model (critical/high/medium/low), and turns it all into a
per-project **security score**, trend charts, downloadable reports and alerts.

Every integration ships with a **mock implementation that is enabled by default**, so the
whole platform (API, worker, dashboard) runs locally with **no credentials and no network
access to third-party services**.

## Why this project

Teams usually run security tools, but the results end up scattered across CI logs,
SonarQube tabs and Slack threads. Nobody can say which service is riskiest today or whether
things are getting better. ShieldOps puts those signals together in one place and makes them
comparable across projects. It also shows how to wire scanners into a web platform *safely*:
it never runs user-supplied shell commands, validates every input strictly, verifies webhook
signatures, encrypts tokens at rest and writes an audit trail.

## Highlights

- **Five integration adapters** (GitHub Actions, SonarQube, Trivy, Docker, pip-audit), each
  with a **real** and a **mock** implementation, selected by environment variable.
- **Parsers for real tool output**: Trivy JSON (schema v2), `pip-audit --format json`,
  SonarQube `/api/issues/search` + `/api/qualitygates/project_status` + `/api/measures/component`,
  and GitHub `workflow_run` payloads, all tested against realistic fixtures.
- **Documented security score** (0-100, A-F grade) combining vulnerabilities, quality gate
  and pipeline health.
- **Reports** in JSON, CSV (formula-injection safe) and printable HTML, with ranked
  **remediation recommendations**.
- **Security first**: fixed-argv scanner execution (never `shell=True`) in ephemeral temp
  workspaces, strict validators for repository URLs, branches and image refs, HMAC-SHA256
  webhook verification with constant-time comparison, Fernet-encrypted tokens, RBAC and audit logs.
- **Background processing** with Celery + Redis in Docker, or **eager in-process** mode for
  local development and tests (no Redis needed).
- **Reusable GitHub Actions workflows** (`workflow_call`) with pinned, least-privilege permissions,
  plus a full CI pipeline for this repository (ruff, bandit, pip-audit, pytest on Postgres,
  tsc, vitest, build, Trivy image scan).

## Table of contents

- [Skills demonstrated](#skills-demonstrated)
- [Architecture](#architecture)
- [CI/CD workflow](#cicd-workflow)
- [Features by module](#features-by-module)
- [Screenshots](#screenshots)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Makefile targets](#makefile-targets)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [SonarQube setup](#sonarqube-setup)
- [Trivy setup](#trivy-setup)
- [GitHub integration](#github-integration)
- [Real vs mock integrations](#real-vs-mock-integrations)
- [Security score methodology](#security-score-methodology)
- [Security considerations](#security-considerations)
- [Example reports](#example-reports)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [License](#license)
- [Author](#author)

## Skills demonstrated

- Python backend engineering: FastAPI, SQLAlchemy 2.0 (typed ORM), Pydantic v2, Alembic migrations
- PostgreSQL schema design (JSONB, window functions, constraints, indexes)
- Asynchronous/background processing with Celery and Redis
- Secure API design: JWT auth, RBAC, input validation, rate limiting, audit logging, secret encryption
- DevSecOps tooling: SonarQube, Trivy, pip-audit, Bandit, Ruff, GitHub Actions, Dependabot, CodeQL
- Integration design: adapter pattern with real/mock implementations, external REST APIs, webhooks (HMAC)
- Safe subprocess execution and threat modelling (command injection, SSRF, CSV injection)
- React + TypeScript frontend: Vite, Tailwind CSS, React Query, React Router, Recharts
- Testing: pytest against real PostgreSQL, Vitest + Testing Library, CI service containers
- Containerisation: multi-stage Dockerfiles, non-root images, docker-compose with optional profiles
- Technical writing: architecture docs, API reference, deployment guide

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        UI["React + TS dashboard<br/>(Vite, Tailwind, React Query, Recharts)"]
    end
    subgraph Platform
        API["FastAPI API<br/>JWT · RBAC · audit log"]
        W["Celery worker + beat<br/>(eager mode locally)"]
        DB[("PostgreSQL 16")]
        R[("Redis<br/>broker")]
    end
    subgraph Adapters["Integration adapters (real | mock)"]
        GH["GitHub Actions adapter"]
        SQ["SonarQube adapter"]
        TV["Trivy adapter<br/>binary | docker"]
        DK["Docker adapter"]
        PA["pip-audit adapter"]
    end
    GitHub[(GitHub REST API)]
    Sonar[(SonarQube server)]
    UI -- REST /api/v1 --> API
    GitHub -- "workflow_run webhook<br/>(HMAC-SHA256)" --> API
    API --> DB
    API -- enqueue --> R --> W
    W --> DB
    API --> GH
    W --> GH & SQ & TV & DK & PA
    GH --> GitHub
    SQ --> Sonar
```

More detail (container view, sequence diagrams, ER diagram, threat model) is in
[ARCHITECTURE.md](ARCHITECTURE.md).

## CI/CD workflow

```mermaid
flowchart LR
    PR["push / pull_request"] --> L["backend-lint<br/>ruff check + format"]
    PR --> S["backend-security<br/>bandit + pip-audit"]
    PR --> T["backend-tests<br/>pytest + Postgres service"]
    PR --> F["frontend<br/>tsc · vitest · vite build"]
    L & S & T --> B["docker-build<br/>api image"]
    F --> B
    B --> V["trivy-image-scan<br/>CRITICAL/HIGH gate + SARIF"]
    PR --> C["CodeQL<br/>python + JS/TS"]
```

Reusable workflows that other repositories can call live in
[`.github/workflows/reusable-*.yml`](.github/workflows) (see [workflows-library/](workflows-library)).

## Features by module

| # | Module | What it does |
|---|--------|--------------|
| 1 | **Projects** | Register projects with a strictly validated `https://github.com/<owner>/<repo>` URL, default branch + extra branches (git ref-name rules), SonarQube key, container images, scan toggles; members with owner/maintainer/viewer roles; encrypted per-project GitHub token; scan history. |
| 2 | **CI/CD** | Ingests GitHub Actions runs by API sync (on demand + every 15 min via Celery beat) or by signed `workflow_run` webhooks; success rate, durations, per-workflow and daily stats; reusable `workflow_call` workflows. |
| 3 | **Code security** | SonarQube issues (bugs, vulnerabilities, code smells), quality gate status and conditions, coverage/duplication metrics; legacy and Clean Code ("impacts") severities mapped to one scale. |
| 4 | **Container security** | Trivy image scans (local binary or throw-away container), OS and language package vulnerabilities, critical/high/medium/low classification, image digest metadata via the Docker adapter. |
| 5 | **Dependency security** | pip-audit on the repo's pinned `requirements.txt` (sanitised), dependency inventory, vulnerable package list, fix versions, scan history; CI-produced reports can be imported. |
| 6 | **Reporting** | Per-project and portfolio reports (JSON / CSV / HTML), vulnerability trends, score trends, ranked remediation recommendations, [documented scoring](docs/security-score.md). |
| 7 | **Dashboard** | Total projects, pipeline success rate, vulnerability counts, quality gates, per-project security overview, recent pipeline runs and scans. |
| 8 | **Notifications** | In-app alerts for pipeline failures, critical vulnerabilities, failed quality gates, scan completion/failure; optional generic webhook and SMTP e-mail channels. |

## Screenshots

Screenshots live in [`docs/screenshots/`](docs/screenshots) (see its README for the capture list).

| Overview | Project detail | Vulnerabilities |
|---|---|---|
| ![Overview](docs/screenshots/overview.png) | ![Project](docs/screenshots/project-detail.png) | ![Vulnerabilities](docs/screenshots/vulnerabilities.png) |

| Pipelines | Container scans | Reports |
|---|---|---|
| ![Pipelines](docs/screenshots/pipelines.png) | ![Containers](docs/screenshots/container-scans.png) | ![Reports](docs/screenshots/reports.png) |

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PyJWT, bcrypt, cryptography (Fernet), httpx |
| Data | PostgreSQL 16 (JSONB), Redis 7 (Celery broker/result backend) |
| Workers | Celery 5 (worker + beat), eager mode for local/dev |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack React Query, React Router, Recharts |
| Scanners | SonarQube (Web API), Trivy, pip-audit, Docker CLI |
| Quality/Sec | Ruff, Bandit, pip-audit, pytest, Vitest, CodeQL, Dependabot, pre-commit |
| Delivery | Docker (multi-stage, non-root), docker-compose, GitHub Actions |

## Quick start

### Option A: Docker Compose (everything)

```bash
cp .env.example .env            # mock integrations, no credentials needed
docker compose up -d --build    # postgres, redis, api, worker, frontend
docker compose exec api python -m app.seed   # optional demo data
# Dashboard: http://localhost:8080   API docs: http://localhost:8000/api/v1/docs
```

Optional local SonarQube (+ its own Postgres): `docker compose --profile sonar up -d`
then open http://localhost:9000.

### Option B: Local backend + frontend (no Docker)

Requirements: Python 3.12+, Node 20+ (tested with Node 24) and a PostgreSQL database.
No Redis is needed: tasks run eagerly in-process.

```bash
# Backend
cd backend
uv venv --python 3.12 .venv          # or: python -m venv .venv
uv pip install --python .venv -e ".[dev]"
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# Need a database? Start a throw-away embedded Postgres (dev-only helper):
python scripts/dev_postgres.py .pgdata    # prints DATABASE_URL=...; keep it running
export DATABASE_URL=postgresql+psycopg2://...   # value printed above

alembic upgrade head
python -m app.seed                   # demo users/projects (local only)
uvicorn app.main:app --reload --port 8000

# Frontend (new shell)
cd frontend
npm ci
npm run dev                          # http://localhost:5173
```

### Demo login (LOCAL ONLY)

`python -m app.seed` creates these accounts. The credentials are public, so use them only on
your own machine; the seed refuses to run when `ENVIRONMENT=production`.

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `ShieldOpsAdmin2026` | platform admin (owner of demo projects) |
| `dev@example.com` | `ShieldOpsDev2026` | maintainer on demo projects |
| `viewer@example.com` | `ShieldOpsView2026` | read-only viewer |

Without the seed, the **first account registered** becomes the administrator.

## Makefile targets

| Target | Description |
|---|---|
| `make install` | Create backend venv + install deps, `npm ci` for the frontend |
| `make dev-backend` / `make dev-frontend` | Run uvicorn (reload) / Vite dev server |
| `make lint` / `make format` | Ruff check + format check, `tsc --noEmit` / auto-format |
| `make security` | Bandit + pip-audit |
| `make test` | Backend + frontend tests (`test-backend`, `test-frontend`) |
| `make migrate` / `make seed` | `alembic upgrade head` / load demo data |
| `make up` / `make down` / `make up-sonar` / `make logs` | docker-compose lifecycle |
| `make build` | Build the frontend and Docker images |
| `make clean` | Remove caches and build output |

## Configuration

All settings are environment variables (see [.env.example](.env.example)).

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `test` or `production` (production disables seeding and plain-HTTP notification webhooks) |
| `DATABASE_URL` | `postgresql+psycopg2://devsecops:devsecops@localhost:5432/devsecops` | PostgreSQL URL (other databases are rejected) |
| `SECRET_KEY` | dev placeholder | JWT signing key; **must** be changed in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime |
| `ALLOW_REGISTRATION` | `true` | Allow self-registration after the first (admin) user |
| `TOKEN_ENCRYPTION_KEY` | empty | Fernet key for tokens at rest (derived from `SECRET_KEY` if empty, dev only) |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Allowed browser origins |
| `CELERY_TASK_ALWAYS_EAGER` | `true` | Run tasks in-process (no Redis). Compose sets `false` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` / `/1` | Redis URLs |
| `GITHUB_MODE` | `mock` | `mock` or `real` |
| `GITHUB_API_URL` | `https://api.github.com` | GitHub (Enterprise) API base URL |
| `GITHUB_WEBHOOK_SECRET` | empty | Webhook HMAC secret; the webhook endpoint returns 503 until set |
| `SONARQUBE_MODE` / `SONARQUBE_URL` / `SONARQUBE_TOKEN` | `mock` / `http://localhost:9000` / empty | SonarQube connection |
| `TRIVY_MODE` | `mock` | `mock`, `binary` (local `trivy`) or `docker` (`aquasec/trivy` container) |
| `TRIVY_BINARY` / `TRIVY_DOCKER_IMAGE` / `TRIVY_TIMEOUT_SECONDS` | `trivy` / `aquasec/trivy:0.58.1` / `600` | Trivy execution |
| `DOCKER_MODE` / `DOCKER_BINARY` | `mock` / `docker` | Image metadata via `docker image inspect` |
| `PIP_AUDIT_MODE` / `PIP_AUDIT_BINARY` / `PIP_AUDIT_TIMEOUT_SECONDS` | `mock` / `pip-audit` / `300` | Dependency auditing |
| `HTTP_TIMEOUT_SECONDS` | `15` | Timeout for outbound HTTP calls |
| `NOTIFICATION_WEBHOOK_URL` | empty | Optional JSON webhook for alert notifications |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` | empty / `587` / ... | Optional e-mail alerts |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Frontend API base (build time) |

## API overview

Base path `/api/v1`. Interactive OpenAPI docs: `/api/v1/docs`. Full reference with examples
and error codes: [docs/API.md](docs/API.md). A Postman collection is in
[postman_collection.json](postman_collection.json).

| Module | Endpoints |
|---|---|
| System | `GET /health`, `GET /health/ready`, `GET /settings/integrations`, `GET /audit-logs` (admin) |
| Auth & users | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `GET /users` (admin), `PATCH /users/{id}` (admin) |
| Projects | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `GET/POST /projects/{id}/members`, `DELETE /projects/{id}/members/{user_id}`, `GET/PUT/DELETE /projects/{id}/credentials/github`, `GET /projects/{id}/security` |
| Scans | `GET/POST /projects/{id}/scans`, `POST /projects/{id}/scans/import`, `GET /scans`, `GET /scans/{id}` |
| Findings | `GET /findings`, `GET /findings/summary`, `GET /dependencies` |
| Pipelines | `POST /projects/{id}/pipelines/sync`, `GET /pipelines/runs`, `GET /pipelines/stats` |
| Code quality | `GET /code-quality/overview` |
| Dashboard | `GET /dashboard/summary` |
| Reports | `GET /reports/projects/{id}?format=json\|csv\|html`, `GET /reports/summary?format=json\|csv`, `GET /reports/trends` |
| Notifications | `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/{id}/read`, `POST /notifications/read-all` |
| Webhooks | `POST /webhooks/github` (HMAC-SHA256 signed) |

## SonarQube setup

1. Start SonarQube locally: `docker compose --profile sonar up -d sonarqube sonar-db`, open
   http://localhost:9000 and change the default admin password.
2. Create a project whose key matches the project's `sonar_project_key` in ShieldOps
   (this repository's own key is in [sonar-project.properties](sonar-project.properties)).
3. Run an analysis, e.g. with the reusable workflow
   [`reusable-sonarqube.yml`](.github/workflows/reusable-sonarqube.yml) or locally with
   `sonar-scanner` (it reads `sonar-project.properties`).
4. Create a **user token** with *Browse* permission on the projects, then set
   `SONARQUBE_MODE=real`, `SONARQUBE_URL` and `SONARQUBE_TOKEN`.
5. Trigger a *Code quality* scan from the project page. ShieldOps calls
   `/api/issues/search`, `/api/qualitygates/project_status` and `/api/measures/component`.

## Trivy setup

- **Docker Compose**: the worker image includes the official Trivy binary (copied from
  `aquasec/trivy`), so `TRIVY_MODE=binary` works inside the worker container.
- **Local binary**: install Trivy ([docs](https://trivy.dev/latest/getting-started/installation/)),
  then set `TRIVY_MODE=binary`.
- **Throw-away container**: `TRIVY_MODE=docker` runs `aquasec/trivy` with `--rm --read-only
  --cap-drop ALL --security-opt no-new-privileges` and writes the report to an ephemeral host
  temp dir.
- Only images **registered on the project** can be scanned, and every image reference is validated
  against an OCI reference regex before it reaches an argv list.
- CI examples: [`reusable-trivy-scan.yml`](.github/workflows/reusable-trivy-scan.yml) and
  [`workflows-library/examples/`](workflows-library/examples). A CI-produced
  `trivy image --format json` report can be imported via `POST /projects/{id}/scans/import`.

## GitHub integration

**Token (per project, optional for public repos).** Use a **fine-grained personal access token**
limited to the selected repositories with these read-only permissions:

| Permission | Access | Used for |
|---|---|---|
| Metadata | Read | Repository lookup / access check |
| Actions | Read | `GET /repos/{owner}/{repo}/actions/runs` |
| Contents | Read | Fetching `requirements.txt` for dependency scans |

The token is checked against the registered repository before it is stored, encrypted with
Fernet (`TOKEN_ENCRYPTION_KEY`), never returned by the API (only a `****abcd` hint), never logged
(a redacting log filter also scrubs token-like strings), and only owners can set or delete it.

**Webhook.** In the repository settings add a webhook to
`https://<your-host>/api/v1/webhooks/github`, content type `application/json`, a random
**secret** (same value as `GITHUB_WEBHOOK_SECRET`), and select **Workflow runs** events.
Each delivery's `X-Hub-Signature-256` is recomputed with HMAC-SHA256 and compared in
constant time (`hmac.compare_digest`). Unsigned or mis-signed requests get `401` and are
audit-logged. Events for repositories that are not registered are ignored.

## Real vs mock integrations

| Integration | Mock (default) | Real implementation | Exercised in this repo's tests |
|---|---|---|---|
| GitHub Actions | Deterministic, time-relative runs per repo; illustrative `requirements.txt` | REST API via httpx (`/actions/runs`, `/repos/{o}/{r}`, `/contents`) | Real adapter tested against an **httpx MockTransport** (request shape, auth header, error mapping). Not run against live GitHub. |
| GitHub webhooks | n/a | HMAC-SHA256 verification + `workflow_run` processing | Fully tested (valid, invalid, missing signature, unregistered repo). |
| SonarQube | Issue catalogue + computed quality gate | Web API via httpx with Bearer token, pagination | Real adapter tested against httpx MockTransport. Not run against a live server. |
| Trivy | Report generated from a CVE catalogue per image | `trivy image` binary or `aquasec/trivy` container | argv construction tested; **not executed** (Trivy not installed on the dev machine). Runs in CI via `aquasecurity/trivy-action`. |
| Docker | Fake digest/size metadata | `docker image inspect` (read-only, never pulls/runs) | argv construction tested; not executed (no Docker on the dev machine). |
| pip-audit | Matches pins against a small advisory table | `pip-audit -r ... --no-deps --disable-pip -f json` | Sanitiser + argv tested. The real CLI is executed by CI (`backend-security` job) on this repo. |

Vulnerability data in the mocks and fixtures (CVE/GHSA IDs) is illustrative sample data for
demonstration, not a live advisory feed.

## Security score methodology

```
score = clamp(100 - vulnerability_penalty - quality_gate_penalty - pipeline_penalty, 0, 100)
vulnerability_penalty = min(60, 10*critical + 5*high + 2*medium + 0.5*low)
quality_gate_penalty  = 15 if failed, 5 if warning, else 0
pipeline_penalty      = 15 * (1 - success_rate over the last 20 completed runs)
grade: A >= 90, B >= 80, C >= 70, D >= 60, else F
```

Only the **latest completed scan per (project, scan type, target)** counts, and SonarQube
code smells are excluded. Full rationale and worked examples: [docs/security-score.md](docs/security-score.md).

## Security considerations

- **No arbitrary command execution**: scanners run from fixed argv lists with `shell=False`,
  a `--` separator before positional arguments, validated arguments, a minimal environment,
  hard timeouts and a fresh `0700` temp directory that is deleted afterwards.
- **Input validation**: strict regexes for GitHub URLs, branch names (git ref rules),
  OCI image references, SonarQube keys and repo file paths; Pydantic models forbid unknown fields
  where it matters; untrusted `requirements.txt` is reduced to pinned `name==version` lines
  (pip options such as `--index-url`, `-e` and `-r` are rejected).
- **Authorization before scanning**: only maintainers/owners of a *registered* project can
  trigger scans, and only for that project's registered branches and images. Non-members get
  `404` (no information leak).
- **No auto-deploy**: the platform only reads and scans artifacts. It never pulls-and-runs or
  deploys images, and the Docker adapter is read-only (`image inspect`).
- **Secrets**: Fernet-encrypted tokens, never returned or logged; `.env.example` only.
- **Webhooks**: HMAC-SHA256, constant-time comparison, 1 MB body limit, 503 if no secret is configured.
- **Auth**: bcrypt (SHA-256 pre-hash), short-lived JWT with required claims, login throttling
  (5 failures / 15 min per email+IP), admin and project-role checks.
- **Audit log** of logins (success/failure/blocked), registrations, user changes, project
  CRUD, membership, credential changes, scan triggers/imports, pipeline syncs, report exports
  and rejected webhooks.
- **Web hardening**: security headers (CSP, `X-Frame-Options`, `nosniff`), restricted CORS,
  CSV formula-injection neutralisation, HTML reports escaped.

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Example reports

- [docs/examples/project-report.json](docs/examples/project-report.json): full per-project report
- [docs/examples/project-report.csv](docs/examples/project-report.csv): findings export
- [docs/examples/portfolio-summary.csv](docs/examples/portfolio-summary.csv): all projects
- [docs/examples/project-report.html](docs/examples/project-report.html): printable HTML (use the browser's *Print to PDF*)

These were generated by the running application from mock-mode demo data.

## Testing

```bash
make test            # or individually:
cd backend && pytest --cov=app        # needs PostgreSQL: TEST_DATABASE_URL or embedded pgserver
cd frontend && npm test               # vitest
```

The backend tests always run against **PostgreSQL**. CI provides a `postgres:16` service
container through `TEST_DATABASE_URL`. Locally, if that variable is unset, the fixtures start
an embedded PostgreSQL via the `pgserver` dev dependency.

| Suite | Result |
|---|---|
| Backend (pytest) | TBD |
| Backend coverage | TBD |
| Frontend (vitest) | TBD |
| Lint / security | TBD |

## Project structure

```
devsecops-automation-pipeline/
├── backend/
│   ├── app/
│   │   ├── adapters/        # real + mock integrations, safe subprocess runner, mock data
│   │   ├── api/routes/      # FastAPI routers per module
│   │   ├── core/            # config, security (JWT, Fernet, HMAC), validators, logging
│   │   ├── db/              # SQLAlchemy base + session
│   │   ├── parsers/         # Trivy, pip-audit, SonarQube, GitHub parsers
│   │   ├── services/        # scans, pipelines, scoring, reporting, notifications, audit
│   │   ├── worker/          # Celery app + tasks
│   │   ├── models.py  schemas.py  main.py  seed.py
│   ├── alembic/             # migrations (source of truth for the schema)
│   ├── tests/               # pytest suite + realistic JSON fixtures
│   └── Dockerfile
├── frontend/                # React + TS + Vite + Tailwind dashboard
├── .github/workflows/       # ci.yml, codeql.yml, reusable-*.yml
├── workflows-library/       # how to consume the reusable workflows + examples
├── docs/                    # API, deployment, scoring, example reports, screenshots
├── docker-compose.yml  sonar-project.properties  Makefile  .env.example
├── ARCHITECTURE.md  PROJECT_SUMMARY.md  postman_collection.json  database_schema.sql
```

## Roadmap

- OSV.dev enrichment so pip-audit findings get CVSS-based severities
- Per-project CI ingest tokens so pipelines can push reports without a user JWT
- SBOM (CycloneDX) generation and licence policy checks
- Finding triage workflow (accept risk / false positive with expiry)
- GitHub App authentication as an alternative to PATs
- Multi-tenant organisations and SSO (OIDC)

## License

[MIT](LICENSE) © 2026 vks-eng

## Author

Built by **vks-eng** · GitHub: https://github.com/vks-eng
