import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, ErrorState, GradeBadge, Loading, PageHeader, StatusPill } from "../components/ui";
import { downloadFile } from "../lib/api";
import { formatPercent } from "../lib/format";
import { usePortfolioSummary, useProjects, useTrends } from "../lib/queries";

export default function ReportsPage() {
  const summary = usePortfolioSummary();
  const projects = useProjects();
  const trends = useTrends(30);
  const [error, setError] = useState<unknown>(null);
  const stamp = new Date().toISOString().slice(0, 10);

  async function download(path: string, format: string, filename: string) {
    setError(null);
    try {
      await downloadFile(path, { format }, filename);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Scan summaries, score trends and downloadable reports with remediation recommendations."
        actions={
          <button type="button" className="btn-primary" onClick={() => download("/reports/summary", "csv", `security-summary-${stamp}.csv`)}>
            <Download size={15} aria-hidden /> Portfolio CSV
          </button>
        }
      />
      {error !== null && <ErrorState error={error} />}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Average security score (30 days)" className="xl:col-span-2">
          <div className="h-56">
            {trends.data && trends.data.scores.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends.data.scores} margin={{ left: -16 }}>
                  <CartesianGrid stroke="#1f2b44" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "#64748f", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#64748f", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#0d1422", border: "1px solid #1f2b44", fontSize: 12 }} />
                  <Line type="monotone" dataKey="average_score" stroke="#22d3ee" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-16 text-center text-sm text-ink-muted">Score history appears after scans complete.</p>
            )}
          </div>
        </Card>
        <Card title="Score methodology">
          <p className="font-mono text-xs leading-relaxed text-ink-muted">
            score = 100 − min(60, 10·C + 5·H + 2·M + 0.5·L) − gate (15 failed / 5 warn) − 15·(1 − pipeline success)
          </p>
          <p className="mt-3 text-xs text-ink-faint">Grades: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F. Latest scan per target counts; code smells excluded.</p>
        </Card>
      </div>

      <Card title="Project reports">
        {summary.isLoading && <Loading />}
        {summary.error && <ErrorState error={summary.error} />}
        {summary.data && (
          <div className="overflow-x-auto">
            <table className="table">
              <thead><tr><th>Project</th><th>Team</th><th>Score</th><th>C / H / M / L</th><th>Quality gate</th><th>Pipelines</th><th>Download</th></tr></thead>
              <tbody>
                {summary.data.map((row) => {
                  const project = projects.data?.find((p) => p.slug === row.project);
                  return (
                    <tr key={row.project}>
                      <td className="font-medium">{row.name}</td>
                      <td className="text-ink-muted">{row.team}</td>
                      <td><GradeBadge grade={row.grade} score={row.score} /></td>
                      <td className="font-mono text-xs"><span className="text-sev-critical">{row.critical}</span> / <span className="text-sev-high">{row.high}</span> / <span className="text-sev-medium">{row.medium}</span> / <span className="text-sev-low">{row.low}</span></td>
                      <td><StatusPill status={row.quality_gate || null} /></td>
                      <td className="font-mono text-xs">{formatPercent(row.pipeline_success_rate, 0)}</td>
                      <td>
                        {project && (
                          <div className="flex gap-1">
                            <button type="button" className="btn-ghost px-2 py-1 text-xs" aria-label={`Download ${row.name} JSON report`} onClick={() => download(`/reports/projects/${project.id}`, "json", `security-report-${row.project}.json`)}><FileJson size={14} aria-hidden /> JSON</button>
                            <button type="button" className="btn-ghost px-2 py-1 text-xs" aria-label={`Download ${row.name} CSV report`} onClick={() => download(`/reports/projects/${project.id}`, "csv", `security-report-${row.project}.csv`)}><FileSpreadsheet size={14} aria-hidden /> CSV</button>
                            <button type="button" className="btn-ghost px-2 py-1 text-xs" aria-label={`Download ${row.name} HTML report`} onClick={() => download(`/reports/projects/${project.id}`, "html", `security-report-${row.project}.html`)}><FileText size={14} aria-hidden /> HTML</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
