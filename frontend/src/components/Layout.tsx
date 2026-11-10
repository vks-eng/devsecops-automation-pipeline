import clsx from "clsx";
import {
  Bell,
  Boxes,
  Code2,
  FileBarChart2,
  FolderGit2,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Package,
  Settings,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
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

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand to-sky-600 text-canvas shadow-[0_0_24px_-6px] shadow-brand">
        <ShieldCheck size={20} aria-hidden />
      </span>
      {!compact && (
        <span className="leading-tight">
          <span className="block text-[15px] font-bold tracking-tight">ShieldOps</span>
          <span className="block text-[10px] uppercase tracking-[0.18em] text-ink-faint">DevSecOps Platform</span>
        </span>
      )}
    </div>
  );
}

function UnreadBadge() {
  const { data } = useUnreadCount();
  if (!data?.unread) return null;
  return (
    <span className="ml-auto rounded-full bg-sev-critical px-1.5 text-[10px] font-bold text-white" aria-label={`${data.unread} unread`}>
      {data.unread > 99 ? "99+" : data.unread}
    </span>
  );
}

export function ProtectedLayout() {
  const { user, loading, logout } = useAuth();
  const location = useLocation();
  if (loading) return <Loading label="Restoring session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-surface/70 backdrop-blur lg:flex">
        <div className="px-5 py-5">
          <Brand />
        </div>
        <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-brand-soft/60 text-brand shadow-[inset_2px_0_0_0] shadow-brand"
                    : "text-ink-muted hover:bg-surface-2 hover:text-ink",
                )
              }
            >
              <Icon size={17} aria-hidden />
              {label}
              {to === "/notifications" && <UnreadBadge />}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-line p-4">
          <p className="truncate text-sm font-medium">{user.full_name || user.email}</p>
          <p className="truncate text-xs text-ink-faint">
            {user.email} · {user.role}
          </p>
          <button type="button" onClick={logout} className="btn-ghost mt-3 w-full justify-center">
            <LogOut size={15} aria-hidden /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-surface/60 px-4 py-3 lg:hidden">
          <Brand compact />
          <nav className="flex gap-1 overflow-x-auto" aria-label="Mobile">
            {NAV.slice(0, 5).map(({ to, icon: Icon, label, end }) => (
              <NavLink key={to} to={to} end={end} aria-label={label} className="rounded-md p-2 text-ink-muted hover:bg-surface-2">
                <Icon size={18} aria-hidden />
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-8 sm:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
