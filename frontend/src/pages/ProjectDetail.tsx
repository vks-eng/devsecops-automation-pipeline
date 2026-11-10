import { Download, ExternalLink, Play, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, ErrorState, GradeBadge, Loading, PageHeader, SeverityBadge, StatusPill } from "../components/ui";
import { downloadFile } from "../lib/api";
import { formatDate, formatPercent, scanTypeLabel } from "../lib/format";
import {
  useMembers,
  useProject,
  useProjectScans,
  useProjectSecurity,
  useSyncPipelines,
  useTriggerScan,
} from "../lib/queries";
import { SEVERITIES, type ScanType } from "../lib/types";

export default function ProjectDetailPage() {
  const id = Number(useParams().id);
  const project = useProject(id);
  const security = useProjectSecurity(id);
  const scans = useProjectScans(id);
  const members = useMembers(id);
  const trigger = useTriggerScan(id);
  const sync = useSyncPipelines(id);
  const [scanType, setScanType] = useState<ScanType>("container");
  const [target, setTarget] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  if (project.isLoading) return <Loading />;
  if (project.error) return <ErrorState error={project.error} />;
  const p = project.data!;
  const canWrite = ["owner", "maintainer", "admin"].includes(p.my_role ?? "");
  const targets = scanType === "container" ? p.container_images : [p.default_branch, ...p.branches];

  async function runScan() {
    setMessage(null);
    const scan = await trigger.mutateAsync({ scan_type: scanType, target: target || null });
    setMessage(`Scan #${scan.id} ${scan.status === "pending" ? "queued" : scan.status}`);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={p.name}
        subtitle={p.description || p.repo_url}
        actions={
          <>
            <a href={p.repo_url} target="_blank" rel="noreferrer noopener" className="btn-ghost">
              <ExternalLink size={15} aria-hidden /> GitHub
            </a>
            <button type="button" className="btn-ghost" onClick={() => downloadFile(`/reports/projects/${id}`, { format: "json" }, `${p.slug}-report.json`)}>
              <Download size={15} aria-hidden /> JSON
            </button>
            <button type="button" className="btn-ghost" onClick={() => downloadFile(`/reports/projects/${id}`, { format: "csv" }, `${p.slug}-report.csv`)}>
              <Download size={15} aria-hidden /> CSV
            </button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <Card title="Security score">
          {security.data ? (
            <>
              <GradeBadge grade={security.data.grade} score={security.data.score} />
              <dl className="mt-3 space-y-1 text-xs text-ink-muted">
                <div className="flex justify-between"><dt>Vulnerability penalty</dt><dd className="font-mono">-{security.data.vulnerability_penalty}</dd></div>
                <div className="flex justify-between"><dt>Quality gate penalty</dt><dd className="font-mono">-{security.data.quality_gate_penalty}</dd></div>
                <div className="flex justify-between"><dt>Pipeline penalty</dt><dd className="font-mono">-{security.data.pipeline_penalty}</dd></div>
              </dl>
            </>
          ) : (
            <Loading />
          )}
        </Card>
        <Card title="Open findings" className="lg:col-span-2">
          <div className="flex flex-wrap gap-2">
            {security.data && SEVERITIES.map((s) => <SeverityBadge key={s} severity={s} count={security.data.counts[s]} />)}
          </div>
          <div className="mt-4 flex gap-6 text-sm">
            <div>
              <p className="text-xs text-ink-faint">Quality gate</p>
              <StatusPill status={security.data?.quality_gate_status} />
            </div>
            <div>
              <p className="text-xs text-ink-faint">Pipeline success</p>
              <p className="font-mono">{formatPercent(security.data?.pipeline_success_rate)}</p>
            </div>
            <div>
              <p className="text-xs text-ink-faint">Your role</p>
              <p className="capitalize">{p.my_role}</p>
            </div>
          </div>
        </Card>
        <Card title="Configuration">
          <dl className="space-y-1.5 text-xs">
            <div><dt className="text-ink-faint">Repository</dt><dd className="font-mono">{p.repo_owner}/{p.repo_name}</dd></div>
            <div><dt className="text-ink-faint">Branches</dt><dd className="font-mono">{[p.default_branch, ...p.branches].join(", ")}</dd></div>
            <div><dt className="text-ink-faint">SonarQube key</dt><dd className="font-mono">{p.sonar_project_key ?? "—"}</dd></div>
            <div><dt className="text-ink-faint">Requirements file</dt><dd className="font-mono">{p.scan_config.requirements_path}</dd></div>
          </dl>
        </Card>
      </div>

      {canWrite && (
        <Card title="Run a scan">
          <div className="flex flex-wrap items-end gap-3">
            <label>
              <span className="label">Scan type</span>
              <select aria-label="Scan type" className="input" value={scanType} onChange={(e) => { setScanType(e.target.value as ScanType); setTarget(""); }}>
                <option value="container">Container (Trivy)</option>
                <option value="dependency">Dependency (pip-audit)</option>
                <option value="code_quality">Code quality (SonarQube)</option>
              </select>
            </label>
            <label>
              <span className="label">{scanType === "container" ? "Registered image" : "Branch"}</span>
              <select aria-label="Target" className="input min-w-64 font-mono" value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">Default</option>
                {targets.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <button type="button" className="btn-primary" onClick={runScan} disabled={trigger.isPending}>
              <Play size={15} aria-hidden /> {trigger.isPending ? "Scanning…" : "Start scan"}
            </button>
            <button type="button" className="btn-ghost" onClick={() => sync.mutate()} disabled={sync.isPending}>
              <RefreshCw size={15} aria-hidden className={sync.isPending ? "animate-spin" : ""} /> Sync pipelines
            </button>
          </div>
          <p className="mt-2 text-xs text-ink-faint">Only images and branches registered on this project can be scanned.</p>
          {message && <p role="status" className="mt-3 text-sm text-ok">{message}</p>}
          {sync.data && <p role="status" className="mt-3 text-sm text-ok">Synced {sync.data.synced} pipeline runs</p>}
          {(trigger.error || sync.error) && <div className="mt-3"><ErrorState error={trigger.error ?? sync.error} /></div>}
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Scan history" className="xl:col-span-2">
          {scans.isLoading ? <Loading /> : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead><tr><th>#</th><th>Type</th><th>Target</th><th>Status</th><th>Findings</th><th>Mode</th><th>When</th></tr></thead>
                <tbody>
                  {scans.data?.map((s) => (
                    <tr key={s.id}>
                      <td className="font-mono text-xs">{s.id}</td>
                      <td>{scanTypeLabel(s.scan_type)}</td>
                      <td className="max-w-56 truncate font-mono text-xs" title={s.target}>{s.target}</td>
                      <td><StatusPill status={s.status} />{s.error && <p className="mt-1 text-xs text-bad">{s.error}</p>}</td>
                      <td className="font-mono text-xs">{s.summary.critical ?? 0}C · {s.summary.high ?? 0}H · {s.summary.medium ?? 0}M</td>
                      <td className="text-xs text-ink-muted">{s.adapter_mode}</td>
                      <td className="text-xs text-ink-muted">{formatDate(s.completed_at ?? s.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Link to={`/vulnerabilities?project_id=${id}`} className="mt-3 inline-block text-xs text-brand">View findings for this project →</Link>
        </Card>
        <Card title="Members">
          <ul className="space-y-2 text-sm">
            {members.data?.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between">
                <span className="truncate">{m.full_name || m.email}<span className="block text-xs text-ink-faint">{m.email}</span></span>
                <span className="rounded bg-surface-3 px-1.5 py-0.5 text-xs capitalize">{m.role}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
