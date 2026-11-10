import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import * as fx from "./fixtures";

export const API = "http://localhost:8000/api/v1";

export const handlers = [
  http.post(`${API}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.password !== "CorrectHorse1") {
      return HttpResponse.json({ detail: "Invalid email or password" }, { status: 401 });
    }
    return HttpResponse.json({ access_token: "test-token", token_type: "bearer", expires_in: 3600 });
  }),
  http.get(`${API}/auth/me`, () => HttpResponse.json(fx.adminUser)),
  http.get(`${API}/dashboard/summary`, () => HttpResponse.json(fx.dashboard)),
  http.get(`${API}/reports/trends`, () => HttpResponse.json(fx.trends)),
  http.get(`${API}/pipelines/stats`, () => HttpResponse.json(fx.stats)),
  http.get(`${API}/findings/top-rules`, () => HttpResponse.json(fx.topRules)),
  http.get(`${API}/findings`, ({ request }) => {
    const severity = new URL(request.url).searchParams.get("severity");
    const items = severity ? fx.findings.items.filter((f) => f.severity === severity) : fx.findings.items;
    return HttpResponse.json({ ...fx.findings, items, total: items.length });
  }),
  http.get(`${API}/projects`, () => HttpResponse.json([fx.project])),
  http.post(`${API}/projects`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...fx.project, ...body, id: 2 }, { status: 201 });
  }),
  http.get(`${API}/notifications/unread-count`, () => HttpResponse.json({ unread: 3 })),
  http.get(`${API}/projects/:id`, () => HttpResponse.json(fx.project)),
  http.get(`${API}/projects/:id/security`, () => HttpResponse.json(fx.dashboard.projects[0])),
  http.get(`${API}/projects/:id/scans`, () => HttpResponse.json([])),
  http.get(`${API}/projects/:id/members`, () =>
    HttpResponse.json([{ user_id: 1, email: "admin@example.com", full_name: "Ada Admin", role: "owner" }]),
  ),
  http.post(`${API}/projects/:id/scans`, async ({ request }) => {
    const body = (await request.json()) as { scan_type: string; target: string | null };
    return HttpResponse.json(
      {
        id: 99,
        project_id: 1,
        scan_type: body.scan_type,
        target: body.target ?? "ghcr.io/acme-demo/payments-api:1.8.2",
        status: "completed",
        adapter_mode: "mock",
        trigger: "manual",
        summary: {},
        quality_gate_status: null,
        error: null,
        created_at: "2026-11-10T09:00:00Z",
        started_at: null,
        completed_at: null,
      },
      { status: 202 },
    );
  }),
];

export const server = setupServer(...handlers);
