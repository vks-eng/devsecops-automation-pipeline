import { AlertOctagon, CheckCheck, GitBranch, ScanSearch, XCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, EmptyState, ErrorState, Loading, PageHeader, SeverityBadge } from "../components/ui";
import { relativeTime } from "../lib/format";
import { useMarkRead, useNotifications } from "../lib/queries";

const ICONS: Record<string, typeof GitBranch> = {
  pipeline_failure: GitBranch,
  critical_vulnerability: AlertOctagon,
  scan_completed: ScanSearch,
  scan_failed: XCircle,
};

export default function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const notifications = useNotifications(unreadOnly);
  const markRead = useMarkRead();
  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        subtitle="Pipeline failures, critical vulnerability alerts and scan results for your projects."
        actions={
          <>
            <label className="flex items-center gap-2 text-sm text-ink-muted">
              <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only
            </label>
            <button type="button" className="btn-ghost" onClick={() => markRead.mutate("all")}>
              <CheckCheck size={15} aria-hidden /> Mark all read
            </button>
          </>
        }
      />
      <Card>
        {notifications.isLoading && <Loading />}
        {notifications.error && <ErrorState error={notifications.error} />}
        {notifications.data && notifications.data.length === 0 && <EmptyState title="You're all caught up" />}
        <ul className="divide-y divide-line">
          {notifications.data?.map((n) => {
            const Icon = ICONS[n.type] ?? ScanSearch;
            return (
              <li key={n.id} className={`flex gap-4 py-4 ${n.read_at ? "opacity-60" : ""}`}>
                <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line bg-surface-2 text-brand">
                  <Icon size={17} aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{n.title}</p>
                    <SeverityBadge severity={n.severity} />
                    {!n.read_at && <span className="h-2 w-2 rounded-full bg-brand" aria-label="unread" />}
                  </div>
                  <p className="mt-1 text-sm text-ink-muted">{n.message}</p>
                  <p className="mt-1 text-xs text-ink-faint">
                    {relativeTime(n.created_at)} · {n.type.replace(/_/g, " ")}
                    {n.link && (
                      <>
                        {" · "}
                        <Link to={n.link.split("?")[0]} className="text-brand">open</Link>
                      </>
                    )}
                  </p>
                </div>
                {!n.read_at && (
                  <button type="button" className="btn-ghost h-fit px-2 py-1 text-xs" onClick={() => markRead.mutate(n.id)}>
                    Mark read
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
