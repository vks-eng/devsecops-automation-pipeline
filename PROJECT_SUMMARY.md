# ShieldOps: DevSecOps Automation Platform (Case Study)

## The problem

Engineering teams run SonarQube, Trivy, pip-audit and GitHub Actions, but the results are
spread across tools, logs and chat threads. Team leads and security owners can't answer simple
questions quickly: *Which service is riskiest right now? Are we getting better? Which fix
removes the most risk?* Wiring scanners into a central platform also carries risk of its own.
A naive implementation that shells out to tools with user-supplied input invites command
injection and unauthorized scanning.

## The solution

ShieldOps is a full-stack platform that registers GitHub repositories, ingests CI/CD runs (API
sync and HMAC-signed webhooks), runs or imports SonarQube, Trivy and pip-audit analyses through
**isolated, swappable adapters**, normalises everything into one severity model and presents it
as a **security score**, trends, downloadable reports, remediation advice and alerts.
Every integration has a **mock mode (the default)**, so the product can be demoed and tested
with zero credentials.

## Key features

- Project registry with strictly validated GitHub URLs, branches, images and SonarQube keys; RBAC (owner/maintainer/viewer + platform admin)
- CI/CD history from GitHub Actions: success rate, durations, per-workflow and daily stats; signed webhooks
- Code quality: SonarQube issues, quality gate + conditions, coverage/duplication
- Container security: Trivy scans with critical/high/medium/low classification and image metadata
- Dependency security: pip-audit with dependency inventory and fix versions; CI report import
- Reporting: JSON / CSV / HTML reports, vulnerability and score trends, ranked remediation plan
- Dashboard with portfolio KPIs and per-project security overview
- Notifications: in-app alerts plus optional webhook and SMTP channels
- Audit log of every security-sensitive action

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · Celery + Redis ·
JWT · React + TypeScript · Vite · Tailwind CSS · React Query · Recharts · Docker / docker-compose ·
GitHub Actions · SonarQube · Trivy · pip-audit · Bandit · Ruff · pytest · Vitest · CodeQL

## Engineering and security practices

- Layered backend: routes → services → pure parsers / adapters → ORM; adapters behind Protocols with real + mock implementations
- Scanner execution hardened: fixed argv, `shell=False`, `--` separators, regex-validated arguments, ephemeral `0700` workspaces, minimal env, timeouts; Trivy optionally in a `--read-only --cap-drop ALL` container
- Authorization before any scan (registered project, maintainer role, registered target only); 404 for non-members
- Secrets: Fernet-encrypted tokens at rest, never returned or logged (log redaction filter)
- HMAC-SHA256 webhook verification with constant-time comparison
- Untrusted `requirements.txt` sanitised to pinned lines only (blocks pip option injection)
- CSV formula-injection protection, escaped HTML reports, security headers, login throttling
- Tests run against **real PostgreSQL** (CI service container; embedded Postgres locally)
- CI: ruff, bandit, pip-audit, pytest + coverage, tsc, vitest, production build, Docker build, Trivy image scan, CodeQL, Dependabot

## Measurable facts

| Metric | Value |
|---|---|
| REST endpoints | 42 (under `/api/v1`) |
| Frontend pages | 12 (incl. login) |
| Integration adapters | 5 interfaces, 11 implementations (6 real, 5 mock) |
| Tool-output parsers | 4 (Trivy, pip-audit, SonarQube, GitHub Actions) |
| Database tables | 11 (+ `alembic_version`) |
| Reusable GitHub workflows | TBD |
| Backend tests / coverage | TBD |
| Frontend tests | TBD |

## What this demonstrates for a client

- I can design and ship a **production-shaped full-stack product**: API, worker, database,
  migrations, SPA, containers, CI, all documented.
- I treat **security as a feature**: threat-modelled command execution, input validation,
  secret handling, RBAC and audit trails, not just a scanner bolted on.
- I build **integration layers that are testable and swappable** (real vs mock), which lowers
  the risk and cost of connecting to third-party systems such as GitHub, SonarQube or cloud APIs.
- I write **clear documentation** (architecture, API, deployment, scoring methodology) so teams
  can own the system after handover.

## Upwork-ready blurb

> I built ShieldOps, a DevSecOps platform that centralises SonarQube, Trivy, pip-audit and GitHub
> Actions results into one dashboard with a documented security score, trend charts, downloadable
> reports and alerts. It's a FastAPI + PostgreSQL + Celery backend with a React/TypeScript
> frontend, hardened scanner execution, HMAC-verified webhooks, encrypted secrets, RBAC and audit
> logging, all running in Docker with a full CI pipeline. I can build the same kind of secure,
> well-tested integration platform for your team.

## GitHub repo settings

**Suggested description** (under 350 characters):

> ShieldOps: a DevSecOps automation platform that aggregates SonarQube, Trivy, pip-audit and GitHub
> Actions into one dashboard with security scores, trends, reports and alerts. FastAPI, PostgreSQL,
> Celery, React + TypeScript, with secure scanner adapters (real + mock).

**Suggested topics:**

`devsecops` `fastapi` `react` `typescript` `postgresql` `trivy` `sonarqube` `github-actions`
`security-scanning` `vulnerability-management` `celery` `docker`
