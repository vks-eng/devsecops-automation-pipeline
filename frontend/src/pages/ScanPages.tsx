import { useState } from "react";
import { Card, EmptyState, ErrorState, Loading, PageHeader, SeverityBadge, SeverityBar, StatusPill } from "../components/ui";
import { formatDate } from "../lib/format";
import { useDependencies, useFindings, useScan, useScans } from "../lib/queries";
import type { Scan } from "../lib/types";
import { FindingsTable } from "./Vulnerabilities";

function ScanHistory({ scans, selected, onSelect }: { scans: Scan[]; selected: number | null; onSelect: (id: number) => void }) {
  if (scans.length === 0) return <EmptyState title="No scans yet">Trigger one from a project page.</EmptyState>;
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead><tr><th>#</th><th>Project</th><th>Target</th><th>Status</th><th className="w-40">Findings</th><th>Completed</th></tr></thead>
        <tbody>
          {scans.map((s) => (
            <tr key={s.id} onClick={() => onSelect(s.id)} className={`cursor-pointer ${selected === s.id ? "bg-brand-soft/30" : ""}`}>
              <td className="font-mono text-xs">{s.id}</td>
              <td>{s.project_name}</td>
              <td className="max-w-72 truncate font-mono text-xs" title={s.target}>{s.target}</td>
              <td><StatusPill status={s.status} /></td>
              <td><SeverityBar counts={s.summary} /><p className="mt-1 font-mono text-[11px] text-ink-muted">{s.summary.critical ?? 0}C · {s.summary.high ?? 0}H · {s.summary.medium ?? 0}M · {s.summary.low ?? 0}L</p></td>
              <td className="text-xs text-ink-muted">{formatDate(s.completed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ImageMeta({ scanId }: { scanId: number }) {
  const scan = useScan(scanId);
  const image = (scan.data?.metadata?.image ?? null) as Record<string, unknown> | null;
  const os = scan.data?.metadata?.os as string | undefined;
  if (!scan.data) return <Loading />;
  return (
    <dl className="grid gap-3 text-xs sm:grid-cols-4">
      <div><dt className="text-ink-faint">Image</dt><dd className="font-mono">{scan.data.target}</dd></div>
      <div><dt className="text-ink-faint">Digest</dt><dd className="truncate font-mono" title={String(image?.digest ?? "")}>{String(image?.digest ?? "—").slice(0, 24)}…</dd></div>
      <div><dt className="text-ink-faint">OS</dt><dd>{os ?? "—"}</dd></div>
      <div><dt className="text-ink-faint">Scanner</dt><dd>Trivy ({scan.data.adapter_mode})</dd></div>
    </dl>
  );
}

export function ContainerScansPage() {
  const scans = useScans({ scan_type: "container", limit: 100 });
  const [selected, setSelected] = useState<number | null>(null);
  const completed = (scans.data ?? []).filter((s) => s.status === "completed");
  const latest = selected ?? completed[0]?.id ?? null;
  return (
    <div className="space-y-6">
      <PageHeader title="Container scans" subtitle="Trivy image scans of registered container images (OS and language packages)." />
      <Card title="Scan history">
        {scans.isLoading && <Loading />}
        {scans.error && <ErrorState error={scans.error} />}
        {scans.data && <ScanHistory scans={scans.data} selected={latest} onSelect={setSelected} />}
      </Card>
      {latest !== null && (
        <Card title={`Scan #${latest} details`}>
          <ImageMeta scanId={latest} />
          <div className="mt-5"><FindingsTableForScan scanId={latest} /></div>
        </Card>
      )}
    </div>
  );
}

function FindingsTableForScan({ scanId }: { scanId: number }) {
  const findings = useFindings({ scan_id: scanId, limit: 200 });
  if (findings.isLoading) return <Loading />;
  if (!findings.data || findings.data.items.length === 0) return <EmptyState title="No vulnerabilities in this image" />;
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead><tr><th>Severity</th><th>CVE</th><th>Package</th><th>Installed</th><th>Fixed</th><th>Title</th></tr></thead>
        <tbody>
          {findings.data.items.map((f) => (
            <tr key={f.id}>
              <td><SeverityBadge severity={f.severity} /></td>
              <td className="font-mono text-xs">{f.reference_url ? <a className="hover:text-brand" href={f.reference_url} target="_blank" rel="noreferrer noopener">{f.rule_id}</a> : f.rule_id}</td>
              <td className="font-mono text-xs">{f.component}</td>
              <td className="font-mono text-xs text-ink-muted">{f.installed_version}</td>
              <td className="font-mono text-xs text-ok">{f.fixed_version ?? <span className="text-ink-faint">—</span>}</td>
              <td className="max-w-md text-sm">{f.title}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DependencyScansPage() {
  const scans = useScans({ scan_type: "dependency", limit: 100 });
  const [vulnerableOnly, setVulnerableOnly] = useState(false);
  const inventory = useDependencies({ vulnerable_only: vulnerableOnly });
  return (
    <div className="space-y-6">
      <PageHeader title="Dependency scans" subtitle="pip-audit results, dependency inventory and vulnerable packages." />
      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Scan history">
          {scans.isLoading && <Loading />}
          {scans.data && <ScanHistory scans={scans.data} selected={null} onSelect={() => undefined} />}
        </Card>
        <Card
          title="Dependency inventory"
          action={
            <label className="flex items-center gap-2 text-xs text-ink-muted">
              <input type="checkbox" checked={vulnerableOnly} onChange={(e) => setVulnerableOnly(e.target.checked)} /> Vulnerable only
            </label>
          }
        >
          {inventory.isLoading && <Loading />}
          {inventory.data && inventory.data.length === 0 && <EmptyState title="No dependencies recorded" />}
          {inventory.data && inventory.data.length > 0 && (
            <div className="max-h-96 overflow-auto">
              <table className="table">
                <thead><tr><th>Package</th><th>Version</th><th>Project</th><th>Vulns</th></tr></thead>
                <tbody>
                  {inventory.data.map((d) => (
                    <tr key={d.id}>
                      <td className="font-mono text-xs">{d.name}</td>
                      <td className="font-mono text-xs">{d.version}</td>
                      <td className="text-xs text-ink-muted">{d.project_name}</td>
                      <td>{d.vulnerable ? <span className="font-mono text-xs text-sev-high">{d.vulnerability_count}</span> : <span className="text-xs text-ok">clean</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
      <Card title="Vulnerable dependencies">
        <FindingsTable category="dependency" />
      </Card>
    </div>
  );
}
