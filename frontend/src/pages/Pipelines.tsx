import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, EmptyState, ErrorState, KpiCard, Loading, PageHeader, Select, StatusPill } from "../components/ui";
import { formatDate, formatDuration, formatPercent } from "../lib/format";
import { usePipelineRuns, usePipelineStats, useProjects } from "../lib/queries";

const PAGE = 20;

export default function PipelinesPage() {
  const stats = usePipelineStats(30);
  const projects = useProjects();
  const [projectId, setProjectId] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [offset, setOffset] = useState(0);
  const runs = usePipelineRuns({ project_id: projectId || undefined, conclusion: conclusion || undefined, limit: PAGE, offset });

  return (
    <div className="space-y-6">
      <PageHeader title="Pipeline executions" subtitle="GitHub Actions runs ingested by API sync and signed webhooks." />
      {stats.data && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Runs (30d)" value={stats.data.total_runs} hint={`${stats.data.in_progress} in progress`} />
          <KpiCard label="Success rate" value={formatPercent(stats.data.success_rate)} hint={`${stats.data.successful} succeeded`} />
          <KpiCard label="Failed" value={<span className="text-bad">{stats.data.failed}</span>} hint="failure / timed out" />
          <KpiCard label="Avg duration" value={formatDuration(stats.data.avg_duration_seconds)} />
        </div>
      )}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Daily results" className="xl:col-span-2">
          <div className="h-60">
            {stats.data && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.data.daily} margin={{ left: -16 }}>
                  <CartesianGrid stroke="#1f2b44" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "#64748f", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                  <YAxis tick={{ fill: "#64748f", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#0d1422", border: "1px solid #1f2b44", fontSize: 12 }} cursor={{ fill: "#ffffff08" }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="success" stackId="a" fill="#34d399" isAnimationActive={false} />
                  <Bar dataKey="failure" stackId="a" fill="#f43f5e" isAnimationActive={false} />
                  <Bar dataKey="other" stackId="a" fill="#64748f" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
        <Card title="By workflow">
          <ul className="space-y-3 text-sm">
            {stats.data?.by_workflow.map((w) => (
              <li key={w.workflow}>
                <div className="flex justify-between"><span>{w.workflow}</span><span className="font-mono text-xs text-ink-muted">{w.success}/{w.total}</span></div>
                <div className="mt-1 h-1.5 rounded-full bg-bad/40"><div className="h-full rounded-full bg-ok" style={{ width: `${(w.success / Math.max(1, w.total)) * 100}%` }} /></div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card
        title="Runs"
        action={
          <div className="flex gap-3">
            <Select label="Project" value={projectId} onChange={(v) => { setProjectId(v); setOffset(0); }} options={[{ value: "", label: "All projects" }, ...(projects.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))]} />
            <Select label="Result" value={conclusion} onChange={(v) => { setConclusion(v); setOffset(0); }} options={[{ value: "", label: "Any" }, { value: "success", label: "Success" }, { value: "failure", label: "Failure" }, { value: "cancelled", label: "Cancelled" }]} />
          </div>
        }
      >
        {runs.isLoading && <Loading />}
        {runs.error && <ErrorState error={runs.error} />}
        {runs.data && runs.data.items.length === 0 && <EmptyState title="No pipeline runs" />}
        {runs.data && runs.data.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="table">
                <thead><tr><th>Workflow</th><th>Project</th><th>Branch / commit</th><th>Event</th><th>Result</th><th>Duration</th><th>Started</th><th /></tr></thead>
                <tbody>
                  {runs.data.items.map((r) => (
                    <tr key={r.id}>
                      <td className="font-medium">{r.workflow_name}<p className="text-xs text-ink-faint">by {r.actor || "—"} · {r.source}</p></td>
                      <td className="text-ink-muted">{r.project_name}</td>
                      <td className="font-mono text-xs">{r.branch}<p className="text-ink-faint">{r.commit_sha.slice(0, 7)}</p></td>
                      <td className="text-xs">{r.event}</td>
                      <td><StatusPill status={r.conclusion ?? r.status} /></td>
                      <td className="font-mono text-xs">{formatDuration(r.duration_seconds)}</td>
                      <td className="text-xs text-ink-muted">{formatDate(r.started_at)}</td>
                      <td>{r.html_url && <a href={r.html_url} target="_blank" rel="noreferrer noopener" aria-label="Open run on GitHub" className="text-ink-muted hover:text-brand"><ExternalLink size={14} /></a>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex items-center justify-between text-xs text-ink-muted">
              <span>{offset + 1}–{Math.min(offset + PAGE, runs.data.total)} of {runs.data.total}</span>
              <div className="flex gap-2">
                <button type="button" className="btn-ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
                <button type="button" className="btn-ghost" disabled={offset + PAGE >= runs.data.total} onClick={() => setOffset(offset + PAGE)}>Next</button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
