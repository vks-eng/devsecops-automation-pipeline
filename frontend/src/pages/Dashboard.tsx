import { Activity, Boxes, FolderGit2, GitBranch, ScanSearch, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  EmptyState,
  ErrorState,
  GradeBadge,
  KpiCard,
  Loading,
  PageHeader,
  SeverityBadge,
  SeverityBar,
  StatusPill,
} from "../components/ui";
import {
  formatDuration,
  formatPercent,
  relativeTime,
  scanTypeLabel,
  severityColor,
  totalOpen,
} from "../lib/format";
import { findingsDelta, successRateDelta } from "../lib/metrics";
import { useDashboard, usePipelineStats, useTopRules, useTrends } from "../lib/queries";
import { SEVERITIES, type DashboardSummary, type Severity } from "../lib/types";

const tooltipStyle = {
  background: "#0d1422",
  border: "1px solid #1f2b44",
  borderRadius: 8,
  color: "#e6ecf5",
  fontSize: 12,
};

function activityFeed(data: DashboardSummary) {
  const scans = data.recent_scans.map((s) => ({
    key: `scan-${s.id}`,
    at: s.completed_at ?? s.created_at,
    icon: <ScanSearch size={15} aria-hidden />,
    text: (
      <>
        <span className="font-medium">{scanTypeLabel(s.scan_type)} scan</span> of{" "}
        <span className="font-mono text-xs text-ink-muted">{s.target}</span> · {s.project_name}
      </>
    ),
    status: s.status,
    critical: s.summary.critical ?? 0,
  }));
  const runs = data.recent_runs.map((r) => ({
    key: `run-${r.id}`,
    at: r.started_at ?? "",
    icon: <GitBranch size={15} aria-hidden />,
    text: (
      <>
        <span className="font-medium">{r.workflow_name}</span> on <span className="font-mono text-xs">{r.branch}</span>{" "}
        · {r.project_name}
      </>
    ),
    status: r.conclusion ?? r.status,
    critical: 0,
  }));
  return [...scans, ...runs].sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, 10);
}

export default function DashboardPage() {
  const dashboard = useDashboard();
  const trends = useTrends(30);
  const stats = usePipelineStats(14);
  const topRules = useTopRules(8);

  if (dashboard.isLoading) return <Loading label="Loading security overview" />;
  if (dashboard.error) return <ErrorState error={dashboard.error} />;
  const data = dashboard.data!;
  const totals = data.vulnerability_totals;
  const open = totalOpen(totals);
  const pieData = SEVERITIES.filter((s) => s !== "info").map((s) => ({ name: s, value: totals[s] }));
  const maxRule = Math.max(1, ...(topRules.data ?? []).map((r) => r.count));

  return (
    <div className="space-y-6">
      <PageHeader title="Security overview" subtitle="Portfolio-wide quality and security posture across registered projects." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Projects" value={data.total_projects} hint={`${data.total_scans} scans recorded`} icon={<FolderGit2 size={18} />} />
        <KpiCard
          label="Open findings"
          value={open}
          delta={findingsDelta(trends.data)}
          deltaGoodWhen="down"
          hint="vs 7 days ago"
          icon={<ShieldAlert size={18} />}
        />
        <KpiCard
          label="Critical + high"
          value={<span className="text-sev-critical">{totals.critical + totals.high}</span>}
          hint={`${totals.critical} critical · ${totals.high} high`}
          icon={<Activity size={18} />}
        />
        <KpiCard
          label="Pipeline success"
          value={formatPercent(data.pipeline.success_rate)}
          delta={successRateDelta(stats.data)}
          deltaGoodWhen="up"
          hint="last 7d vs prior 7d"
          icon={<GitBranch size={18} />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Open findings trend (30 days)" className="xl:col-span-2">
          {trends.data ? (
            <div className="h-64" data-testid="trend-chart">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends.data.vulnerabilities} margin={{ left: -16, right: 8 }}>
                  <defs>
                    {(["critical", "high", "medium", "low"] as Severity[]).map((s) => (
                      <linearGradient key={s} id={`g-${s}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={severityColor[s]} stopOpacity={0.45} />
                        <stop offset="100%" stopColor={severityColor[s]} stopOpacity={0.02} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid stroke="#1f2b44" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "#64748f", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                  <YAxis tick={{ fill: "#64748f", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {(["low", "medium", "high", "critical"] as Severity[]).map((s) => (
                    <Area
                      key={s}
                      type="monotone"
                      dataKey={s}
                      stackId="1"
                      stroke={severityColor[s]}
                      fill={`url(#g-${s})`}
                      strokeWidth={1.5}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Loading />
          )}
        </Card>

        <Card title="Severity distribution">
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pieData} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fill: "#94a3bd", fontSize: 12 }} width={64} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#ffffff08" }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  {pieData.map((d) => (
                    <Cell key={d.name} fill={severityColor[d.name]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {SEVERITIES.map((s) => (
              <SeverityBadge key={s} severity={s} count={totals[s]} />
            ))}
          </div>
          <div className="mt-5 grid grid-cols-3 gap-2 text-center text-xs">
            {(["passed", "failed", "none"] as const).map((g) => (
              <div key={g} className="rounded-lg border border-line bg-surface-2 py-2">
                <p className="text-lg font-semibold">{data.quality_gates[g]}</p>
                <p className="capitalize text-ink-faint">{g === "none" ? "no gate" : `gate ${g}`}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Project security overview" className="xl:col-span-2">
          {data.projects.length === 0 ? (
            <EmptyState title="No projects yet">Register a repository on the Projects page.</EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Score</th>
                    <th className="w-48">Open findings</th>
                    <th>Quality gate</th>
                    <th>Pipelines</th>
                    <th>Last scan</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data.projects]
                    .sort((a, b) => a.score - b.score)
                    .map((p) => (
                      <tr key={p.project_id}>
                        <td>
                          <Link to={`/projects/${p.project_id}`} className="font-medium hover:text-brand">
                            {p.project_name}
                          </Link>
                          <p className="text-xs text-ink-faint">{p.team || "—"}</p>
                        </td>
                        <td>
                          <GradeBadge grade={p.grade} score={p.score} />
                        </td>
                        <td>
                          <SeverityBar counts={p.counts} />
                          <p className="mt-1 font-mono text-[11px] text-ink-muted">
                            {p.counts.critical}C · {p.counts.high}H · {p.counts.medium}M · {p.counts.low}L
                          </p>
                        </td>
                        <td>
                          <StatusPill status={p.quality_gate_status} />
                        </td>
                        <td className="font-mono text-xs">{formatPercent(p.pipeline_success_rate, 0)}</td>
                        <td className="text-xs text-ink-muted">{relativeTime(p.last_scan_at)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Top rules & CVEs">
          {topRules.data && topRules.data.length > 0 ? (
            <ul className="space-y-3" data-testid="top-rules">
              {topRules.data.map((r) => (
                <li key={`${r.category}-${r.rule_id}`}>
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="truncate font-mono text-ink" title={r.title}>
                      {r.rule_id}
                    </span>
                    <span className="shrink-0 text-ink-muted">
                      {r.count} · {r.projects} proj
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-surface-3">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${(r.count / maxRule) * 100}%`, background: severityColor[r.severity] }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No findings yet" />
          )}
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Recent activity">
          <ol className="relative space-y-4 border-l border-line pl-5">
            {activityFeed(data).map((item) => (
              <li key={item.key} className="relative">
                <span className="absolute -left-[29px] grid h-6 w-6 place-items-center rounded-full border border-line bg-surface-2 text-brand">
                  {item.icon}
                </span>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  {item.text}
                  <StatusPill status={item.status} />
                  {item.critical > 0 && <SeverityBadge severity="critical" count={item.critical} />}
                </div>
                <p className="text-xs text-ink-faint">{relativeTime(item.at)}</p>
              </li>
            ))}
          </ol>
        </Card>

        <Card title="Recent pipeline runs" action={<Link to="/pipelines" className="text-xs text-brand">View all</Link>}>
          <table className="table">
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Project</th>
                <th>Result</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_runs.map((r) => (
                <tr key={r.id}>
                  <td>
                    <span className="font-medium">{r.workflow_name}</span>
                    <p className="font-mono text-[11px] text-ink-faint">{r.branch}</p>
                  </td>
                  <td className="text-ink-muted">{r.project_name}</td>
                  <td>
                    <StatusPill status={r.conclusion ?? r.status} />
                  </td>
                  <td className="font-mono text-xs">{formatDuration(r.duration_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <p className="flex items-center gap-2 text-xs text-ink-faint">
        <Boxes size={13} aria-hidden /> Scores follow the documented methodology in docs/security-score.md.
      </p>
    </div>
  );
}
