// Types mirroring the backend Pydantic schemas / JSON responses (app/schemas.py, routes).

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];
export type SeverityCounts = Record<Severity, number>;
export type ScanType = "code_quality" | "container" | "dependency";
export type ScanStatus = "pending" | "running" | "completed" | "failed";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "member";
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ScanConfig {
  requirements_path: string;
  enable_code_quality: boolean;
  enable_container: boolean;
  enable_dependency: boolean;
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  description: string;
  team: string;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  default_branch: string;
  branches: string[];
  sonar_project_key: string | null;
  container_images: string[];
  scan_config: ScanConfig;
  owner_id: number;
  created_at: string;
  updated_at: string;
  my_role: string | null;
}

export interface ProjectCreate {
  name: string;
  repo_url: string;
  team?: string;
  description?: string;
  default_branch?: string;
  branches?: string[];
  sonar_project_key?: string | null;
  container_images?: string[];
}

export interface Member {
  user_id: number;
  email: string;
  full_name: string;
  role: string;
}

export interface Scan {
  id: number;
  project_id: number;
  scan_type: ScanType;
  target: string;
  status: ScanStatus;
  adapter_mode: string;
  trigger: string;
  summary: Partial<SeverityCounts> & { total?: number; code_smells?: number };
  quality_gate_status: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  project_name?: string | null;
}

export interface ScanDetail extends Scan {
  metadata: Record<string, unknown>;
}

export interface Finding {
  id: number;
  scan_id: number;
  project_id: number;
  category: ScanType;
  finding_type: "vulnerability" | "bug" | "code_smell";
  severity: Severity;
  rule_id: string;
  title: string;
  description: string;
  component: string;
  installed_version: string | null;
  fixed_version: string | null;
  file_path: string | null;
  line: number | null;
  reference_url: string | null;
  recommendation: string;
  created_at: string;
  project_name?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface DependencyItem {
  id: number;
  scan_id: number;
  project_id: number;
  name: string;
  version: string;
  ecosystem: string;
  vulnerable: boolean;
  vulnerability_count: number;
  project_name?: string | null;
}

export interface PipelineRun {
  id: number;
  project_id: number;
  external_id: string;
  workflow_name: string;
  branch: string;
  commit_sha: string;
  event: string;
  status: string;
  conclusion: string | null;
  actor: string;
  html_url: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  source: string;
  project_name?: string | null;
}

export interface PipelineStats {
  days: number;
  total_runs: number;
  completed_runs: number;
  in_progress: number;
  successful: number;
  failed: number;
  success_rate: number | null;
  avg_duration_seconds: number | null;
  daily: { date: string; success: number; failure: number; other: number }[];
  by_workflow: { workflow: string; total: number; success: number }[];
}

export interface ProjectOverview {
  project_id: number;
  project_name: string;
  slug: string;
  team: string;
  counts: SeverityCounts;
  quality_gate_status: string | null;
  pipeline_success_rate: number | null;
  last_scan_at: string | null;
  score: number;
  grade: string;
  vulnerability_penalty: number;
  quality_gate_penalty: number;
  pipeline_penalty: number;
}

export interface DashboardSummary {
  total_projects: number;
  total_scans: number;
  average_score: number | null;
  vulnerability_totals: SeverityCounts;
  pipeline: { window_days: number; by_conclusion: Record<string, number>; success_rate: number | null };
  quality_gates: Record<"passed" | "failed" | "warning" | "none", number>;
  projects: ProjectOverview[];
  recent_runs: {
    id: number;
    project_id: number;
    project_name: string | null;
    workflow_name: string;
    branch: string;
    status: string;
    conclusion: string | null;
    started_at: string | null;
    duration_seconds: number | null;
    html_url: string;
  }[];
  recent_scans: {
    id: number;
    project_id: number;
    project_name: string | null;
    scan_type: ScanType;
    target: string;
    status: ScanStatus;
    summary: Scan["summary"];
    created_at: string;
    completed_at: string | null;
  }[];
}

export interface TrendPoint extends SeverityCounts {
  date: string;
}

export interface Trends {
  vulnerabilities: TrendPoint[];
  scores: { date: string; average_score: number }[];
}

export interface TopRule {
  rule_id: string;
  category: ScanType;
  title: string;
  count: number;
  projects: number;
  severity: Severity;
}

export interface CodeQualityRow {
  project_id: number;
  project_name: string;
  sonar_project_key: string | null;
  scan_id: number | null;
  quality_gate_status: string | null;
  completed_at: string | null;
  adapter_mode: string | null;
  summary: Scan["summary"];
  by_type: Partial<Record<"bug" | "vulnerability" | "code_smell", number>>;
  measures: Record<string, string>;
  conditions: { metric: string; status: string; actual: string; threshold: string; comparator: string }[];
}

export interface Notification {
  id: number;
  project_id: number | null;
  type: string;
  severity: Severity;
  title: string;
  message: string;
  link: string;
  read_at: string | null;
  created_at: string;
}

export interface IntegrationStatus {
  integrations: {
    name: string;
    key: string;
    mode: string;
    configured: boolean;
    details: string;
    webhook_secret_configured?: boolean;
  }[];
  background_processing: string;
  notification_channels: { in_app: boolean; webhook: boolean; email: boolean };
  registration_open: boolean;
}

export interface AuditLog {
  id: number;
  actor_id: number | null;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  outcome: string;
  ip_address: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SummaryRow {
  project: string;
  name: string;
  team: string;
  score: number;
  grade: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  quality_gate: string;
  pipeline_success_rate: number | null;
  last_scan_at: string;
}
