import { Card, EmptyState, ErrorState, Loading, PageHeader, StatusPill } from "../components/ui";
import { formatDate } from "../lib/format";
import { useCodeQuality } from "../lib/queries";
import { FindingsTable } from "./Vulnerabilities";

export default function CodeQualityPage() {
  const overview = useCodeQuality();
  return (
    <div className="space-y-6">
      <PageHeader title="Code quality" subtitle="SonarQube quality gates, issues and metrics per project." />
      {overview.isLoading && <Loading />}
      {overview.error && <ErrorState error={overview.error} />}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {overview.data?.map((row) => (
          <Card key={row.project_id} title={row.project_name}>
            {row.scan_id === null ? (
              <EmptyState title="Not analysed yet">{row.sonar_project_key ? "Run a code quality scan" : "No SonarQube key"}</EmptyState>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <StatusPill status={row.quality_gate_status} />
                  <span className="font-mono text-[11px] text-ink-faint">{row.sonar_project_key}</span>
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
                  {(["bug", "vulnerability", "code_smell"] as const).map((k) => (
                    <div key={k} className="rounded-lg border border-line bg-surface-2 py-2">
                      <dd className="text-lg font-semibold">{row.by_type[k] ?? 0}</dd>
                      <dt className="text-[10px] uppercase tracking-wide text-ink-faint">{k.replace("_", " ")}s</dt>
                    </div>
                  ))}
                </dl>
                <dl className="mt-4 space-y-1 text-xs">
                  <div className="flex justify-between"><dt className="text-ink-muted">Coverage</dt><dd className="font-mono">{row.measures.coverage ?? "—"}%</dd></div>
                  <div className="flex justify-between"><dt className="text-ink-muted">Duplication</dt><dd className="font-mono">{row.measures.duplicated_lines_density ?? "—"}%</dd></div>
                  <div className="flex justify-between"><dt className="text-ink-muted">Lines of code</dt><dd className="font-mono">{row.measures.ncloc ?? "—"}</dd></div>
                </dl>
                <ul className="mt-4 space-y-1 border-t border-line pt-3 text-xs">
                  {row.conditions.map((c) => (
                    <li key={c.metric} className="flex justify-between gap-2">
                      <span className="truncate text-ink-muted">{c.metric}</span>
                      <span className={c.status === "ERROR" ? "text-bad" : "text-ok"}>{c.actual} ({c.comparator} {c.threshold})</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-[11px] text-ink-faint">Analysed {formatDate(row.completed_at)} · {row.adapter_mode}</p>
              </>
            )}
          </Card>
        ))}
      </div>
      <Card title="Open SonarQube issues">
        <FindingsTable category="code_quality" />
      </Card>
    </div>
  );
}
