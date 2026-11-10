import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Query } from "./api";
import type {
  AuditLog,
  CodeQualityRow,
  DashboardSummary,
  DependencyItem,
  Finding,
  IntegrationStatus,
  Member,
  Notification,
  Page,
  PipelineRun,
  PipelineStats,
  Project,
  ProjectCreate,
  ProjectOverview,
  Scan,
  ScanDetail,
  ScanType,
  SummaryRow,
  TopRule,
  Trends,
} from "./types";

export const useDashboard = () =>
  useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<DashboardSummary>("/dashboard/summary") });

export const useTrends = (days = 30, projectId?: number) =>
  useQuery({
    queryKey: ["trends", days, projectId],
    queryFn: () => api.get<Trends>("/reports/trends", { days, project_id: projectId }),
  });

export const useTopRules = (limit = 8) =>
  useQuery({ queryKey: ["top-rules", limit], queryFn: () => api.get<TopRule[]>("/findings/top-rules", { limit }) });

export const useProjects = () => useQuery({ queryKey: ["projects"], queryFn: () => api.get<Project[]>("/projects") });

export const useProject = (id: number) =>
  useQuery({ queryKey: ["projects", id], queryFn: () => api.get<Project>(`/projects/${id}`) });

export const useProjectSecurity = (id: number) =>
  useQuery({
    queryKey: ["projects", id, "security"],
    queryFn: () => api.get<ProjectOverview>(`/projects/${id}/security`),
  });

export const useMembers = (id: number) =>
  useQuery({ queryKey: ["projects", id, "members"], queryFn: () => api.get<Member[]>(`/projects/${id}/members`) });

export const useProjectScans = (id: number) =>
  useQuery({
    queryKey: ["projects", id, "scans"],
    queryFn: () => api.get<Scan[]>(`/projects/${id}/scans`, { limit: 50 }),
  });

export const useScans = (query: Query) =>
  useQuery({ queryKey: ["scans", query], queryFn: () => api.get<Scan[]>("/scans", query) });

export const useScan = (id: number | null) =>
  useQuery({
    queryKey: ["scan", id],
    queryFn: () => api.get<ScanDetail>(`/scans/${id}`),
    enabled: id !== null,
  });

export const useFindings = (query: Query) =>
  useQuery({
    queryKey: ["findings", query],
    queryFn: () => api.get<Page<Finding>>("/findings", query),
    placeholderData: (prev) => prev,
  });

export const useDependencies = (query: Query) =>
  useQuery({ queryKey: ["dependencies", query], queryFn: () => api.get<DependencyItem[]>("/dependencies", query) });

export const usePipelineRuns = (query: Query) =>
  useQuery({
    queryKey: ["pipeline-runs", query],
    queryFn: () => api.get<Page<PipelineRun>>("/pipelines/runs", query),
    placeholderData: (prev) => prev,
  });

export const usePipelineStats = (days = 30) =>
  useQuery({ queryKey: ["pipeline-stats", days], queryFn: () => api.get<PipelineStats>("/pipelines/stats", { days }) });

export const useCodeQuality = () =>
  useQuery({ queryKey: ["code-quality"], queryFn: () => api.get<CodeQualityRow[]>("/code-quality/overview") });

export const usePortfolioSummary = () =>
  useQuery({ queryKey: ["report-summary"], queryFn: () => api.get<SummaryRow[]>("/reports/summary") });

export const useNotifications = (unreadOnly = false) =>
  useQuery({
    queryKey: ["notifications", unreadOnly],
    queryFn: () => api.get<Notification[]>("/notifications", { unread_only: unreadOnly, limit: 100 }),
  });

export const useUnreadCount = () =>
  useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.get<{ unread: number }>("/notifications/unread-count"),
    refetchInterval: 60_000,
  });

export const useIntegrations = () =>
  useQuery({ queryKey: ["integrations"], queryFn: () => api.get<IntegrationStatus>("/settings/integrations") });

export const useAuditLogs = (enabled: boolean) =>
  useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => api.get<AuditLog[]>("/audit-logs", { limit: 50 }),
    enabled,
  });

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectCreate) => api.post<Project>("/projects", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useTriggerScan(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { scan_type: ScanType; target?: string | null }) =>
      api.post<Scan>(`/projects/${projectId}/scans`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects", projectId] });
      void qc.invalidateQueries({ queryKey: ["scans"] });
      void qc.invalidateQueries({ queryKey: ["findings"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
      void qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useSyncPipelines(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ synced: number }>(`/projects/${projectId}/pipelines/sync`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["pipeline-runs"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number | "all") =>
      id === "all" ? api.post("/notifications/read-all") : api.post(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}
