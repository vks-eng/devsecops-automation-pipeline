# Trivy usage examples

```bash
# Scan an image and write the JSON report ShieldOps understands (schema v2)
trivy image --format json --output trivy-report.json --scanners vuln python:3.12-slim

# Fail a pipeline on fixable CRITICAL/HIGH vulnerabilities
trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 my-service:latest

# Throw-away container (same hardening ShieldOps uses in TRIVY_MODE=docker)
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp -v "$PWD:/out" aquasec/trivy:0.58.1 \
  image --format json --output /out/trivy-report.json --quiet -- nginx:1.27

# Import the report into ShieldOps (the image must be registered on the project)
curl -X POST "$SHIELDOPS_URL/api/v1/projects/1/scans/import" \
  -H "Authorization: Bearer $SHIELDOPS_TOKEN" -H "Content-Type: application/json" \
  -d "{\"scan_type\":\"container\",\"target\":\"nginx:1.27\",\"report\":$(cat trivy-report.json)}"
```
