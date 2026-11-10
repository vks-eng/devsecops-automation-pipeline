import clsx from "clsx";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Inbox, Loader2, Minus } from "lucide-react";
import type { ReactNode } from "react";
import { gradeColor, severityLabel } from "../lib/format";
import type { Severity } from "../lib/types";

const sevClasses: Record<Severity, string> = {
  critical: "bg-sev-critical/15 text-sev-critical ring-sev-critical/40",
  high: "bg-sev-high/15 text-sev-high ring-sev-high/40",
  medium: "bg-sev-medium/15 text-sev-medium ring-sev-medium/40",
  low: "bg-sev-low/15 text-sev-low ring-sev-low/40",
  info: "bg-sev-info/15 text-sev-info ring-sev-info/40",
};

export function SeverityBadge({ severity, count }: { severity: Severity; count?: number }) {
  return (
    <span
      data-testid={`severity-${severity}`}
      className={clsx(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset",
        sevClasses[severity],
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {severityLabel[severity]}
      {count !== undefined && <span className="font-mono">{count}</span>}
    </span>
  );
}

const statusTone: Record<string, string> = {
  success: "text-ok bg-ok/10 ring-ok/30",
  completed: "text-ok bg-ok/10 ring-ok/30",
  passed: "text-ok bg-ok/10 ring-ok/30",
  failure: "text-bad bg-bad/10 ring-bad/30",
  failed: "text-bad bg-bad/10 ring-bad/30",
  timed_out: "text-bad bg-bad/10 ring-bad/30",
  warning: "text-warn bg-warn/10 ring-warn/30",
  running: "text-brand bg-brand/10 ring-brand/30",
  in_progress: "text-brand bg-brand/10 ring-brand/30",
  pending: "text-ink-muted bg-surface-3 ring-line-strong",
  queued: "text-ink-muted bg-surface-3 ring-line-strong",
  cancelled: "text-ink-muted bg-surface-3 ring-line-strong",
};

export function StatusPill({ status }: { status: string | null | undefined }) {
  const value = status ?? "none";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1 ring-inset",
        statusTone[value] ?? "text-ink-muted bg-surface-3 ring-line-strong",
      )}
    >
      {value.replace("_", " ")}
    </span>
  );
}

export function GradeBadge({ grade, score }: { grade: string; score?: number }) {
  return (
    <span className="inline-flex items-baseline gap-1.5" title="Security score (see docs/security-score.md)">
      <span className={clsx("text-lg font-bold", gradeColor(grade))}>{grade}</span>
      {score !== undefined && <span className="font-mono text-xs text-ink-muted">{score.toFixed(1)}</span>}
    </span>
  );
}

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("card p-5", className)}>
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="card-title">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  delta,
  deltaGoodWhen = "down",
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  delta?: number | null;
  deltaGoodWhen?: "up" | "down";
  icon?: ReactNode;
}) {
  const hasDelta = delta !== undefined && delta !== null;
  const good = hasDelta && (deltaGoodWhen === "down" ? delta <= 0 : delta >= 0);
  const Icon = !hasDelta || delta === 0 ? Minus : delta > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <div className="card relative overflow-hidden p-5">
      <div className="flex items-start justify-between">
        <p className="card-title">{label}</p>
        {icon && <span className="text-brand/80">{icon}</span>}
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
      <div className="mt-2 flex items-center gap-2 text-xs">
        {hasDelta && (
          <span
            data-testid="kpi-delta"
            className={clsx(
              "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-medium",
              delta === 0 ? "bg-surface-3 text-ink-muted" : good ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad",
            )}
          >
            <Icon size={12} aria-hidden />
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
        {hint && <span className="text-ink-faint">{hint}</span>}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-12 text-sm text-ink-muted">
      <Loader2 className="animate-spin" size={16} aria-hidden /> {label}…
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Something went wrong";
  return (
    <div role="alert" className="flex items-center gap-3 rounded-lg border border-bad/40 bg-bad/10 p-4 text-sm text-bad">
      <AlertTriangle size={16} aria-hidden /> {message}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <Inbox className="text-ink-faint" size={28} aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {children && <div className="text-xs text-ink-muted">{children}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SeverityBar({ counts }: { counts: Partial<Record<Severity, number>> }) {
  const order: Severity[] = ["critical", "high", "medium", "low"];
  const total = order.reduce((s, k) => s + (counts[k] ?? 0), 0);
  if (total === 0) return <div className="h-1.5 w-full rounded-full bg-ok/40" title="No open findings" />;
  return (
    <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-3" aria-label="Severity distribution">
      {order.map((sev) =>
        counts[sev] ? (
          <span
            key={sev}
            className={clsx("h-full", {
              "bg-sev-critical": sev === "critical",
              "bg-sev-high": sev === "high",
              "bg-sev-medium": sev === "medium",
              "bg-sev-low": sev === "low",
            })}
            style={{ width: `${((counts[sev] ?? 0) / total) * 100}%` }}
          />
        ) : null,
      )}
    </div>
  );
}

export function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex flex-col">
      <span className="label">{label}</span>
      <select className="input min-w-36" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
