import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { AlertOctagon, CheckCheck, GitBranch, ScanSearch, XCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, EmptyState, ErrorState, Loading, PageHeader, SeverityBadge } from "../components/ui";
import { relativeTime } from "../lib/format";
import { useMarkRead, useNotifications } from "../lib/queries";
const ICONS = {
    pipeline_failure: GitBranch,
    critical_vulnerability: AlertOctagon,
    scan_completed: ScanSearch,
    scan_failed: XCircle,
};
export default function NotificationsPage() {
    const [unreadOnly, setUnreadOnly] = useState(false);
    const notifications = useNotifications(unreadOnly);
    const markRead = useMarkRead();
    return (_jsxs("div", { className: "space-y-6", children: [_jsx(PageHeader, { title: "Notifications", subtitle: "Pipeline failures, critical vulnerability alerts and scan results for your projects.", actions: _jsxs(_Fragment, { children: [_jsxs("label", { className: "flex items-center gap-2 text-sm text-ink-muted", children: [_jsx("input", { type: "checkbox", checked: unreadOnly, onChange: (e) => setUnreadOnly(e.target.checked) }), " Unread only"] }), _jsxs("button", { type: "button", className: "btn-ghost", onClick: () => markRead.mutate("all"), children: [_jsx(CheckCheck, { size: 15, "aria-hidden": true }), " Mark all read"] })] }) }), _jsxs(Card, { children: [notifications.isLoading && _jsx(Loading, {}), notifications.error && _jsx(ErrorState, { error: notifications.error }), notifications.data && notifications.data.length === 0 && _jsx(EmptyState, { title: "You're all caught up" }), _jsx("ul", { className: "divide-y divide-line", children: notifications.data?.map((n) => {
                            const Icon = ICONS[n.type] ?? ScanSearch;
                            return (_jsxs("li", { className: `flex gap-4 py-4 ${n.read_at ? "opacity-60" : ""}`, children: [_jsx("span", { className: "mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line bg-surface-2 text-brand", children: _jsx(Icon, { size: 17, "aria-hidden": true }) }), _jsxs("div", { className: "min-w-0 flex-1", children: [_jsxs("div", { className: "flex flex-wrap items-center gap-2", children: [_jsx("p", { className: "font-medium", children: n.title }), _jsx(SeverityBadge, { severity: n.severity }), !n.read_at && _jsx("span", { className: "h-2 w-2 rounded-full bg-brand", "aria-label": "unread" })] }), _jsx("p", { className: "mt-1 text-sm text-ink-muted", children: n.message }), _jsxs("p", { className: "mt-1 text-xs text-ink-faint", children: [relativeTime(n.created_at), " \u00B7 ", n.type.replace(/_/g, " "), n.link && (_jsxs(_Fragment, { children: [" · ", _jsx(Link, { to: n.link.split("?")[0], className: "text-brand", children: "open" })] }))] })] }), !n.read_at && (_jsx("button", { type: "button", className: "btn-ghost h-fit px-2 py-1 text-xs", onClick: () => markRead.mutate(n.id), children: "Mark read" }))] }, n.id));
                        }) })] })] }));
}
