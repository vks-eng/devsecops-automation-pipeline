# Reusable GitHub Actions workflows

ShieldOps ships three reusable workflows (`on: workflow_call`) in
[`.github/workflows/`](../.github/workflows). Other repositories can call them so every team gets
the same quality and security gates.

| Workflow | Does | Inputs | Secrets |
|---|---|---|---|
| `reusable-python-quality.yml` | ruff, bandit, pip-audit (JSON artifact), pytest | `working-directory`, `python-version`, `requirements-file`, `run-tests`, `fail-on-audit` | none |
| `reusable-trivy-scan.yml` | builds an image locally (never pushed) and scans it with Trivy; JSON report artifact + severity gate | `context`, `dockerfile`, `image-name`, `severity`, `fail-build` | none |
| `reusable-sonarqube.yml` | sonar-scanner + quality-gate wait | `project-key`, `sources` | `SONAR_TOKEN`, `SONAR_HOST_URL` |

## Least privilege

- Every workflow and job declares `permissions: contents: read`. None of them need write
  scopes because they don't push, comment, upload SARIF or deploy.
- `actions/checkout` uses `persist-credentials: false`, so later steps can't reuse the token.
- Secrets are passed explicitly (`secrets:`), never with `secrets: inherit`.
- Actions are pinned to release tags. For production, pin to full commit SHAs (Dependabot's
  `github-actions` ecosystem keeps them current).

## Example caller

See [examples/caller-example.yml](examples/caller-example.yml). Results can be pushed into
ShieldOps with `POST /api/v1/projects/{id}/scans/import` (Trivy JSON or pip-audit JSON).

These workflows are syntax-valid YAML, but this repository's own CI does not call them, so they
have not been run end-to-end.
