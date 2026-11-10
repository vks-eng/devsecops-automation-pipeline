import { ChevronDown, ChevronRight, Search } from "lucide-react";
import { Fragment, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Card, EmptyState, ErrorState, Loading, PageHeader, SeverityBadge } from "../components/ui";
import { scanTypeLabel } from "../lib/format";
import { useFindings, useProjects } from "../lib/queries";
import { SEVERITIES, type ScanType, type Severity } from "../lib/types";

const PAGE = 25;

export function FindingsTable({ category, projectId }: { category?: ScanType; projectId?: string }) {
  const [severity, setSeverity] = useState<Severity | "">("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<number | null>(null);
  const findings = useFindings({ category, severity: severity || undefined, q: q || undefined, project_id: projectId || undefined, limit: PAGE, offset });

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Severity filter" className="flex flex-wrap gap-1">
          {(["", ...SEVERITIES] as const).map((s) => (
            <button
              key={s || "all"}
              type="button"
              aria-pressed={severity === s}
              onClick={() => { setSeverity(s); setOffset(0); }}
              className={`rounded-md border px-2.5 py-1 text-xs capitalize transition-colors ${severity === s ? "border-brand bg-brand-soft/60 text-brand" : "border-line bg-surface-2 text-ink-muted hover:text-ink"}`}
            >
              {s || "All"}
            </button>
          ))}
        </div>
        <label className="relative ml-auto">
          <span className="sr-only">Search findings</span>
          <Search size={14} className="pointer-events-none absolute top-2.5 left-2.5 text-ink-faint" aria-hidden />
          <input className="input w-64 pl-8" placeholder="Search CVE, rule, package…" value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
        </label>
      </div>
      {findings.isLoading && <Loading />}
      {findings.error && <ErrorState error={findings.error} />}
      {findings.data && findings.data.items.length === 0 && <EmptyState title="No open findings match these filters" />}
      {findings.data && findings.data.items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="table">
              <thead><tr><th className="w-8" /><th>Severity</th><th>ID</th><th>Title</th><th>Component</th><th>Fix</th><th>Project</th>{!category && <th>Source</th>}</tr></thead>
              <tbody>
                {findings.data.items.map((f) => (
                  <Fragment key={f.id}>
                    <tr className="cursor-pointer" onClick={() => setOpen(open === f.id ? null : f.id)}>
                      <td>{open === f.id ? <ChevronDown size={14} aria-hidden /> : <ChevronRight size={14} aria-hidden />}</td>
                      <td><SeverityBadge severity={f.severity} /></td>
                      <td className="font-mono text-xs whitespace-nowrap">{f.rule_id}</td>
                      <td className="max-w-md">{f.title}</td>
                      <td className="font-mono text-xs">{f.component}{f.installed_version && <span className="text-ink-faint"> {f.installed_version}</span>}</td>
                      <td className="font-mono text-xs text-ok">{f.fixed_version ?? <span className="text-ink-faint">none</span>}</td>
                      <td className="text-xs text-ink-muted">{f.project_name}</td>
                      {!category && <td className="text-xs">{scanTypeLabel(f.category)}</td>}
                    </tr>
                    {open === f.id && (
                      <tr className="bg-surface-2/50">
                        <td />
                        <td colSpan={category ? 6 : 7} className="text-sm">
                          {f.description && <p className="text-ink-muted">{f.description}</p>}
                          <p className="mt-2"><span className="font-semibold text-brand">Remediation: </span>{f.recommendation}</p>
                          {f.file_path && <p className="mt-1 font-mono text-xs text-ink-faint">{f.file_path}{f.line ? `:${f.line}` : ""}</p>}
                          {f.reference_url && <a className="mt-1 inline-block text-xs text-brand" href={f.reference_url} target="_blank" rel="noreferrer noopener">Advisory →</a>}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-ink-muted">
            <span>{offset + 1}–{Math.min(offset + PAGE, findings.data.total)} of {findings.data.total}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
              <button type="button" className="btn-ghost" disabled={offset + PAGE >= findings.data.total} onClick={() => setOffset(offset + PAGE)}>Next</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function VulnerabilitiesPage() {
  const [params, setParams] = useSearchParams();
  const projects = useProjects();
  const projectId = params.get("project_id") ?? "";
  const category = (params.get("category") ?? "") as ScanType | "";
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };
  return (
    <div className="space-y-6">
      <PageHeader title="Vulnerability reports" subtitle="Open findings from the latest scan of every registered target." />
      <Card
        action={
          <div className="flex gap-3">
            <label className="flex flex-col"><span className="label">Project</span>
              <select className="input" value={projectId} onChange={(e) => update("project_id", e.target.value)}>
                <option value="">All projects</option>
                {projects.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            <label className="flex flex-col"><span className="label">Source</span>
              <select className="input" value={category} onChange={(e) => update("category", e.target.value)}>
                <option value="">All sources</option>
                <option value="container">Container</option>
                <option value="dependency">Dependency</option>
                <option value="code_quality">Code quality</option>
              </select>
            </label>
          </div>
        }
      >
        <FindingsTable key={`${projectId}-${category}`} projectId={projectId} category={category || undefined} />
      </Card>
    </div>
  );
}
