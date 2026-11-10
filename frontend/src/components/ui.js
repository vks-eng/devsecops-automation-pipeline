import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import clsx from "clsx";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Inbox, Loader2, Minus } from "lucide-react";
import { gradeColor, severityLabel } from "../lib/format";
const sevClasses = {
    critical: "bg-sev-critical/15 text-sev-critical ring-sev-critical/40",
    high: "bg-sev-high/15 text-sev-high ring-sev-high/40",
    medium: "bg-sev-medium/15 text-sev-medium ring-sev-medium/40",
    low: "bg-sev-low/15 text-sev-low ring-sev-low/40",
    info: "bg-sev-info/15 text-sev-info ring-sev-info/40",
};
export function SeverityBadge({ severity, count }) {
    return (_jsxs("span", { "data-testid": `severity-${severity}`, className: clsx("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset", sevClasses[severity]), children: [_jsx("span", { className: "h-1.5 w-1.5 rounded-full bg-current", "aria-hidden": true }), severityLabel[severity], count !== undefined && _jsx("span", { className: "font-mono", children: count })] }));
}
const statusTone = {
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
export function StatusPill({ status }) {
    const value = status ?? "none";
    return (_jsx("span", { className: clsx("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1 ring-inset", statusTone[value] ?? "text-ink-muted bg-surface-3 ring-line-strong"), children: value.replace("_", " ") }));
}
export function GradeBadge({ grade, score }) {
    return (_jsxs("span", { className: "inline-flex items-baseline gap-1.5", title: "Security score (see docs/security-score.md)", children: [_jsx("span", { className: clsx("text-lg font-bold", gradeColor(grade)), children: grade }), score !== undefined && _jsx("span", { className: "font-mono text-xs text-ink-muted", children: score.toFixed(1) })] }));
}
export function Card({ title, action, children, className, }) {
    return (_jsxs("section", { className: clsx("card p-5", className), children: [(title || action) && (_jsxs("header", { className: "mb-4 flex items-center justify-between gap-3", children: [title && _jsx("h2", { className: "card-title", children: title }), action] })), children] }));
}
export function KpiCard({ label, value, hint, delta, deltaGoodWhen = "down", icon, }) {
    const hasDelta = delta !== undefined && delta !== null;
    const good = hasDelta && (deltaGoodWhen === "down" ? delta <= 0 : delta >= 0);
    const Icon = !hasDelta || delta === 0 ? Minus : delta > 0 ? ArrowUpRight : ArrowDownRight;
    return (_jsxs("div", { className: "card relative overflow-hidden p-5", children: [_jsxs("div", { className: "flex items-start justify-between", children: [_jsx("p", { className: "card-title", children: label }), icon && _jsx("span", { className: "text-brand/80", children: icon })] }), _jsx("p", { className: "mt-3 text-3xl font-semibold tracking-tight", children: value }), _jsxs("div", { className: "mt-2 flex items-center gap-2 text-xs", children: [hasDelta && (_jsxs("span", { "data-testid": "kpi-delta", className: clsx("inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-medium", delta === 0 ? "bg-surface-3 text-ink-muted" : good ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"), children: [_jsx(Icon, { size: 12, "aria-hidden": true }), Math.abs(delta).toFixed(1), "%"] })), hint && _jsx("span", { className: "text-ink-faint", children: hint })] })] }));
}
export function Loading({ label = "Loading" }) {
    return (_jsxs("div", { role: "status", className: "flex items-center justify-center gap-2 py-12 text-sm text-ink-muted", children: [_jsx(Loader2, { className: "animate-spin", size: 16, "aria-hidden": true }), " ", label, "\u2026"] }));
}
export function ErrorState({ error }) {
    const message = error instanceof Error ? error.message : "Something went wrong";
    return (_jsxs("div", { role: "alert", className: "flex items-center gap-3 rounded-lg border border-bad/40 bg-bad/10 p-4 text-sm text-bad", children: [_jsx(AlertTriangle, { size: 16, "aria-hidden": true }), " ", message] }));
}
export function EmptyState({ title, children }) {
    return (_jsxs("div", { className: "flex flex-col items-center justify-center gap-2 py-12 text-center", children: [_jsx(Inbox, { className: "text-ink-faint", size: 28, "aria-hidden": true }), _jsx("p", { className: "text-sm font-medium", children: title }), children && _jsx("div", { className: "text-xs text-ink-muted", children: children })] }));
}
export function PageHeader({ title, subtitle, actions }) {
    return (_jsxs("div", { className: "mb-6 flex flex-wrap items-end justify-between gap-4", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-2xl font-semibold tracking-tight", children: title }), subtitle && _jsx("p", { className: "mt-1 text-sm text-ink-muted", children: subtitle })] }), actions && _jsx("div", { className: "flex flex-wrap items-center gap-2", children: actions })] }));
}
export function SeverityBar({ counts }) {
    const order = ["critical", "high", "medium", "low"];
    const total = order.reduce((s, k) => s + (counts[k] ?? 0), 0);
    if (total === 0)
        return _jsx("div", { className: "h-1.5 w-full rounded-full bg-ok/40", title: "No open findings" });
    return (_jsx("div", { className: "flex h-1.5 w-full overflow-hidden rounded-full bg-surface-3", "aria-label": "Severity distribution", children: order.map((sev) => counts[sev] ? (_jsx("span", { className: clsx("h-full", {
                "bg-sev-critical": sev === "critical",
                "bg-sev-high": sev === "high",
                "bg-sev-medium": sev === "medium",
                "bg-sev-low": sev === "low",
            }), style: { width: `${((counts[sev] ?? 0) / total) * 100}%` } }, sev)) : null) }));
}
export function Select({ label, value, onChange, options, }) {
    return (_jsxs("label", { className: "flex flex-col", children: [_jsx("span", { className: "label", children: label }), _jsx("select", { className: "input min-w-36", value: value, onChange: (e) => onChange(e.target.value), children: options.map((o) => (_jsx("option", { value: o.value, children: o.label }, o.value))) })] }));
}
