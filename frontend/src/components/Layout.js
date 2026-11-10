import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import clsx from "clsx";
import { Bell, Boxes, Code2, FileBarChart2, FolderGit2, GitBranch, LayoutDashboard, LogOut, Package, Settings, ShieldAlert, ShieldCheck, } from "lucide-react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useUnreadCount } from "../lib/queries";
import { Loading } from "./ui";
const NAV = [
    { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
    { to: "/projects", label: "Projects", icon: FolderGit2 },
    { to: "/pipelines", label: "Pipelines", icon: GitBranch },
    { to: "/code-quality", label: "Code quality", icon: Code2 },
    { to: "/vulnerabilities", label: "Vulnerabilities", icon: ShieldAlert },
    { to: "/containers", label: "Container scans", icon: Boxes },
    { to: "/dependencies", label: "Dependency scans", icon: Package },
    { to: "/reports", label: "Reports", icon: FileBarChart2 },
    { to: "/notifications", label: "Notifications", icon: Bell },
    { to: "/settings", label: "Settings", icon: Settings },
];
export function Brand({ compact = false }) {
    return (_jsxs("div", { className: "flex items-center gap-2.5", children: [_jsx("span", { className: "grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand to-sky-600 text-canvas shadow-[0_0_24px_-6px] shadow-brand", children: _jsx(ShieldCheck, { size: 20, "aria-hidden": true }) }), !compact && (_jsxs("span", { className: "leading-tight", children: [_jsx("span", { className: "block text-[15px] font-bold tracking-tight", children: "ShieldOps" }), _jsx("span", { className: "block text-[10px] uppercase tracking-[0.18em] text-ink-faint", children: "DevSecOps Platform" })] }))] }));
}
function UnreadBadge() {
    const { data } = useUnreadCount();
    if (!data?.unread)
        return null;
    return (_jsx("span", { className: "ml-auto rounded-full bg-sev-critical px-1.5 text-[10px] font-bold text-white", "aria-label": `${data.unread} unread`, children: data.unread > 99 ? "99+" : data.unread }));
}
export function ProtectedLayout() {
    const { user, loading, logout } = useAuth();
    const location = useLocation();
    if (loading)
        return _jsx(Loading, { label: "Restoring session" });
    if (!user)
        return _jsx(Navigate, { to: "/login", replace: true, state: { from: location.pathname } });
    return (_jsxs("div", { className: "flex min-h-full", children: [_jsxs("aside", { className: "sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-surface/70 backdrop-blur lg:flex", children: [_jsx("div", { className: "px-5 py-5", children: _jsx(Brand, {}) }), _jsx("nav", { className: "flex-1 space-y-0.5 px-3", "aria-label": "Main", children: NAV.map(({ to, label, icon: Icon, end }) => (_jsxs(NavLink, { to: to, end: end, className: ({ isActive }) => clsx("group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors", isActive
                                ? "bg-brand-soft/60 text-brand shadow-[inset_2px_0_0_0] shadow-brand"
                                : "text-ink-muted hover:bg-surface-2 hover:text-ink"), children: [_jsx(Icon, { size: 17, "aria-hidden": true }), label, to === "/notifications" && _jsx(UnreadBadge, {})] }, to))) }), _jsxs("div", { className: "border-t border-line p-4", children: [_jsx("p", { className: "truncate text-sm font-medium", children: user.full_name || user.email }), _jsxs("p", { className: "truncate text-xs text-ink-faint", children: [user.email, " \u00B7 ", user.role] }), _jsxs("button", { type: "button", onClick: logout, className: "btn-ghost mt-3 w-full justify-center", children: [_jsx(LogOut, { size: 15, "aria-hidden": true }), " Sign out"] })] })] }), _jsxs("div", { className: "flex min-w-0 flex-1 flex-col", children: [_jsxs("header", { className: "flex items-center justify-between border-b border-line bg-surface/60 px-4 py-3 lg:hidden", children: [_jsx(Brand, { compact: true }), _jsx("nav", { className: "flex gap-1 overflow-x-auto", "aria-label": "Mobile", children: NAV.slice(0, 5).map(({ to, icon: Icon, label, end }) => (_jsx(NavLink, { to: to, end: end, "aria-label": label, className: "rounded-md p-2 text-ink-muted hover:bg-surface-2", children: _jsx(Icon, { size: 18, "aria-hidden": true }) }, to))) })] }), _jsx("main", { className: "mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-8 sm:py-8", children: _jsx(Outlet, {}) })] })] }));
}
