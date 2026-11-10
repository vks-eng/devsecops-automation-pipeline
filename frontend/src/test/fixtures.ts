import type { DashboardSummary, Finding, Page, PipelineStats, Project, TopRule, Trends, User } from "../lib/types";

export const adminUser: User = {
  id: 1,
  email: "admin@example.com",
  full_name: "Ada Admin",
  role: "admin",
  is_active: true,
  created_at: "2026-11-01T10:00:00Z",
};

export const project: Project = {
  id: 1,
  name: "Payments API",
  slug: "payments-api",
  description: "Card payment processing service",
  team: "Payments",
  repo_url: "https://github.com/acme-demo/payments-api",
  repo_owner: "acme-demo",
  repo_name: "payments-api",
  default_branch: "main",
  branches: ["develop"],
  sonar_project_key: "acme_payments-api",
  container_images: ["ghcr.io/acme-demo/payments-api:1.8.2"],
  scan_config: { requirements_path: "requirements.txt", enable_code_quality: true, enable_container: true, enable_dependency: true },
  owner_id: 1,
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
  my_role: "owner",
};

export const dashboard: DashboardSummary = {
  total_projects: 1,
  total_scans: 3,
  average_score: 42.5,
  vulnerability_totals: { critical: 2, high: 3, medium: 5, low: 1, info: 0 },
  pipeline: { window_days: 30, by_conclusion: { success: 8, failure: 2 }, success_rate: 0.8 },
  quality_gates: { passed: 0, failed: 1, warning: 0, none: 0 },
  projects: [
    {
      project_id: 1,
      project_name: "Payments API",
      slug: "payments-api",
      team: "Payments",
      counts: { critical: 2, high: 3, medium: 5, low: 1, info: 0 },
      quality_gate_status: "failed",
      pipeline_success_rate: 0.8,
      last_scan_at: "2026-11-10T09:00:00Z",
      score: 42.5,
      grade: "F",
      vulnerability_penalty: 45.5,
      quality_gate_penalty: 15,
      pipeline_penalty: 3,
    },
  ],
  recent_runs: [
    {
      id: 7,
      project_id: 1,
      project_name: "Payments API",
      workflow_name: "CI",
      branch: "main",
      status: "completed",
      conclusion: "failure",
      started_at: "2026-11-10T08:00:00Z",
      duration_seconds: 312,
      html_url: "https://github.com/acme-demo/payments-api/actions/runs/7",
    },
  ],
  recent_scans: [
    {
      id: 3,
      project_id: 1,
      project_name: "Payments API",
      scan_type: "container",
      target: "ghcr.io/acme-demo/payments-api:1.8.2",
      status: "completed",
      summary: { critical: 2, high: 1, medium: 0, low: 0, info: 0, total: 3 },
      created_at: "2026-11-10T09:00:00Z",
      completed_at: "2026-11-10T09:00:05Z",
    },
  ],
};

const day = (i: number) => new Date(Date.UTC(2026, 9, 12 + i)).toISOString().slice(0, 10);
export const trends: Trends = {
  vulnerabilities: Array.from({ length: 30 }, (_, i) => ({
    date: day(i),
    critical: 2,
    high: 3,
    medium: i < 23 ? 9 : 5,
    low: 1,
    info: 0,
  })),
  scores: [{ date: day(29), average_score: 42.5 }],
};

export const stats: PipelineStats = {
  days: 14,
  total_runs: 10,
  completed_runs: 10,
  in_progress: 0,
  successful: 8,
  failed: 2,
  success_rate: 0.8,
  avg_duration_seconds: 300,
  daily: Array.from({ length: 14 }, (_, i) => ({ date: day(i + 16), success: i < 7 ? 1 : 2, failure: i < 7 ? 1 : 0, other: 0 })),
  by_workflow: [{ workflow: "CI", total: 10, success: 8 }],
};

export const topRules: TopRule[] = [
  { rule_id: "CVE-2023-45853", category: "container", title: "zlib overflow", count: 3, projects: 1, severity: "critical" },
];

export const findings: Page<Finding> = {
  total: 2,
  limit: 25,
  offset: 0,
  items: [
    {
      id: 11,
      scan_id: 3,
      project_id: 1,
      category: "container",
      finding_type: "vulnerability",
      severity: "critical",
      rule_id: "CVE-2023-45853",
      title: "zlib: integer overflow",
      description: "MiniZip in zlib through 1.3 has an integer overflow.",
      component: "zlib1g",
      installed_version: "1:1.2.13.dfsg-1",
      fixed_version: null,
      file_path: "image (debian 12.5)",
      line: null,
      reference_url: "https://avd.aquasec.com/nvd/cve-2023-45853",
      recommendation: "No fixed version of zlib1g is available yet.",
      created_at: "2026-11-10T09:00:05Z",
      project_name: "Payments API",
    },
    {
      id: 12,
      scan_id: 4,
      project_id: 1,
      category: "dependency",
      finding_type: "vulnerability",
      severity: "medium",
      rule_id: "GHSA-j8r2-6x86-q33q",
      title: "GHSA-j8r2-6x86-q33q in requests 2.28.2",
      description: "Proxy-Authorization header leak.",
      component: "requests",
      installed_version: "2.28.2",
      fixed_version: "2.31.0",
      file_path: null,
      line: null,
      reference_url: null,
      recommendation: "Upgrade requests from 2.28.2 to 2.31.0 or later and re-lock.",
      created_at: "2026-11-10T09:00:05Z",
      project_name: "Payments API",
    },
  ],
};
