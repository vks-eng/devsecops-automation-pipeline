import type { Severity, SeverityCounts } from "./types";

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function relativeTime(value: string | null | undefined, now: Date = new Date()): string {
  if (!value) return "—";
  const diff = (now.getTime() - new Date(value).getTime()) / 1000;
  if (Number.isNaN(diff)) return "—";
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export function formatPercent(rate: number | null | undefined, digits = 1): string {
  if (rate === null || rate === undefined) return "—";
  return `${(rate * 100).toFixed(digits)}%`;
}

export function totalOpen(counts: Partial<SeverityCounts> | undefined): number {
  if (!counts) return 0;
  return (counts.critical ?? 0) + (counts.high ?? 0) + (counts.medium ?? 0) + (counts.low ?? 0);
}

/** Percentage change between two values; null when there is no baseline. */
export function percentChange(current: number, previous: number): number | null {
  if (previous === 0) return current === 0 ? 0 : null;
  return ((current - previous) / previous) * 100;
}

export const severityLabel: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

export const severityColor: Record<Severity, string> = {
  critical: "#f43f5e",
  high: "#fb923c",
  medium: "#facc15",
  low: "#60a5fa",
  info: "#94a3b8",
};

export function scanTypeLabel(type: string): string {
  return { code_quality: "Code quality", container: "Container", dependency: "Dependency" }[type] ?? type;
}

export function gradeColor(grade: string): string {
  return (
    { A: "text-ok", B: "text-emerald-300", C: "text-warn", D: "text-sev-high", F: "text-sev-critical" }[grade] ??
    "text-ink-muted"
  );
}
