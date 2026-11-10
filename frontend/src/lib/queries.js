import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
export const useDashboard = () => useQuery({ queryKey: ["dashboard"], queryFn: () => api.get("/dashboard/summary") });
export const useTrends = (days = 30, projectId) => useQuery({
    queryKey: ["trends", days, projectId],
    queryFn: () => api.get("/reports/trends", { days, project_id: projectId }),
});
export const useTopRules = (limit = 8) => useQuery({ queryKey: ["top-rules", limit], queryFn: () => api.get("/findings/top-rules", { limit }) });
export const useProjects = () => useQuery({ queryKey: ["projects"], queryFn: () => api.get("/projects") });
export const useProject = (id) => useQuery({ queryKey: ["projects", id], queryFn: () => api.get(`/projects/${id}`) });
export const useProjectSecurity = (id) => useQuery({
    queryKey: ["projects", id, "security"],
    queryFn: () => api.get(`/projects/${id}/security`),
});
export const useMembers = (id) => useQuery({ queryKey: ["projects", id, "members"], queryFn: () => api.get(`/projects/${id}/members`) });
export const useProjectScans = (id) => useQuery({
    queryKey: ["projects", id, "scans"],
    queryFn: () => api.get(`/projects/${id}/scans`, { limit: 50 }),
});
export const useScans = (query) => useQuery({ queryKey: ["scans", query], queryFn: () => api.get("/scans", query) });
export const useScan = (id) => useQuery({
    queryKey: ["scan", id],
    queryFn: () => api.get(`/scans/${id}`),
    enabled: id !== null,
});
export const useFindings = (query) => useQuery({
    queryKey: ["findings", query],
    queryFn: () => api.get("/findings", query),
    placeholderData: (prev) => prev,
});
export const useDependencies = (query) => useQuery({ queryKey: ["dependencies", query], queryFn: () => api.get("/dependencies", query) });
export const usePipelineRuns = (query) => useQuery({
    queryKey: ["pipeline-runs", query],
    queryFn: () => api.get("/pipelines/runs", query),
    placeholderData: (prev) => prev,
});
export const usePipelineStats = (days = 30) => useQuery({ queryKey: ["pipeline-stats", days], queryFn: () => api.get("/pipelines/stats", { days }) });
export const useCodeQuality = () => useQuery({ queryKey: ["code-quality"], queryFn: () => api.get("/code-quality/overview") });
export const usePortfolioSummary = () => useQuery({ queryKey: ["report-summary"], queryFn: () => api.get("/reports/summary") });
export const useNotifications = (unreadOnly = false) => useQuery({
    queryKey: ["notifications", unreadOnly],
    queryFn: () => api.get("/notifications", { unread_only: unreadOnly, limit: 100 }),
});
export const useUnreadCount = () => useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.get("/notifications/unread-count"),
    refetchInterval: 60_000,
});
export const useIntegrations = () => useQuery({ queryKey: ["integrations"], queryFn: () => api.get("/settings/integrations") });
export const useAuditLogs = (enabled) => useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => api.get("/audit-logs", { limit: 50 }),
    enabled,
});
export function useCreateProject() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body) => api.post("/projects", body),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
    });
}
export function useTriggerScan(projectId) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body) => api.post(`/projects/${projectId}/scans`, body),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["projects", projectId] });
            void qc.invalidateQueries({ queryKey: ["scans"] });
            void qc.invalidateQueries({ queryKey: ["findings"] });
            void qc.invalidateQueries({ queryKey: ["dashboard"] });
            void qc.invalidateQueries({ queryKey: ["notifications"] });
        },
    });
}
export function useSyncPipelines(projectId) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: () => api.post(`/projects/${projectId}/pipelines/sync`),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["pipeline-runs"] });
            void qc.invalidateQueries({ queryKey: ["dashboard"] });
        },
    });
}
export function useMarkRead() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (id) => id === "all" ? api.post("/notifications/read-all") : api.post(`/notifications/${id}/read`),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
    });
}
