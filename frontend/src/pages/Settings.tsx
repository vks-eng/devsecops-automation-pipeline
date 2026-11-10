import { Card, ErrorState, Loading, PageHeader, StatusPill } from "../components/ui";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useAuditLogs, useIntegrations } from "../lib/queries";

export default function SettingsPage() {
  const { user } = useAuth();
  const integrations = useIntegrations();
  const audit = useAuditLogs(user?.role === "admin");

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" subtitle="Integration modes, notification channels and the audit trail." />
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Integrations" className="xl:col-span-2">
          {integrations.isLoading && <Loading />}
          {integrations.error && <ErrorState error={integrations.error} />}
          {integrations.data && (
            <table className="table">
              <thead><tr><th>Integration</th><th>Mode</th><th>Endpoint / binary</th><th>Configured</th></tr></thead>
              <tbody>
                {integrations.data.integrations.map((i) => (
                  <tr key={i.key}>
                    <td className="font-medium">{i.name}</td>
                    <td>
                      <span className={`rounded px-1.5 py-0.5 font-mono text-xs ${i.mode === "mock" ? "bg-warn/10 text-warn" : "bg-ok/10 text-ok"}`}>{i.mode}</span>
                    </td>
                    <td className="font-mono text-xs text-ink-muted">{i.details}</td>
                    <td className="text-xs">{i.configured ? "yes" : "no"}{i.webhook_secret_configured !== undefined && ` · webhook secret ${i.webhook_secret_configured ? "set" : "not set"}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="mt-3 text-xs text-ink-faint">Modes are set with environment variables (GITHUB_MODE, SONARQUBE_MODE, TRIVY_MODE, DOCKER_MODE, PIP_AUDIT_MODE). Secrets are never shown.</p>
        </Card>
        <Card title="Platform">
          {integrations.data && (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-ink-muted">Background jobs</dt><dd>{integrations.data.background_processing}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-muted">In-app alerts</dt><dd>on</dd></div>
              <div className="flex justify-between"><dt className="text-ink-muted">Webhook channel</dt><dd>{integrations.data.notification_channels.webhook ? "on" : "off"}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-muted">E-mail channel</dt><dd>{integrations.data.notification_channels.email ? "on" : "off"}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-muted">Self-registration</dt><dd>{integrations.data.registration_open ? "open" : "closed"}</dd></div>
            </dl>
          )}
          <div className="mt-5 border-t border-line pt-4 text-sm">
            <p className="font-medium">{user?.full_name}</p>
            <p className="text-xs text-ink-faint">{user?.email} · {user?.role}</p>
          </div>
        </Card>
      </div>
      <Card title="Audit log">
        {user?.role !== "admin" ? (
          <p className="text-sm text-ink-muted">The audit log is visible to platform administrators.</p>
        ) : audit.isLoading ? (
          <Loading />
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Resource</th><th>Outcome</th><th>IP</th></tr></thead>
              <tbody>
                {audit.data?.map((a) => (
                  <tr key={a.id}>
                    <td className="text-xs text-ink-muted">{formatDate(a.created_at)}</td>
                    <td className="text-xs">{a.actor_email || "—"}</td>
                    <td className="font-mono text-xs">{a.action}</td>
                    <td className="font-mono text-xs text-ink-muted">{a.resource_type}{a.resource_id && `:${a.resource_id}`}</td>
                    <td><StatusPill status={a.outcome === "success" ? "success" : a.outcome === "failure" || a.outcome === "rejected" ? "failure" : "warning"} /></td>
                    <td className="font-mono text-xs text-ink-faint">{a.ip_address}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
