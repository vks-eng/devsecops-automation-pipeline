import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Card, EmptyState, ErrorState, Loading, PageHeader, SeverityBadge, SeverityBar, StatusPill } from "../components/ui";
import { formatDate } from "../lib/format";
import { useDependencies, useFindings, useScan, useScans } from "../lib/queries";
import { FindingsTable } from "./Vulnerabilities";
function ScanHistory({ scans, selected, onSelect }) {
    if (scans.length === 0)
        return _jsx(EmptyState, { title: "No scans yet", children: "Trigger one from a project page." });
    return (_jsx("div", { className: "overflow-x-auto", children: _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "#" }), _jsx("th", { children: "Project" }), _jsx("th", { children: "Target" }), _jsx("th", { children: "Status" }), _jsx("th", { className: "w-40", children: "Findings" }), _jsx("th", { children: "Completed" })] }) }), _jsx("tbody", { children: scans.map((s) => (_jsxs("tr", { onClick: () => onSelect(s.id), className: `cursor-pointer ${selected === s.id ? "bg-brand-soft/30" : ""}`, children: [_jsx("td", { className: "font-mono text-xs", children: s.id }), _jsx("td", { children: s.project_name }), _jsx("td", { className: "max-w-72 truncate font-mono text-xs", title: s.target, children: s.target }), _jsx("td", { children: _jsx(StatusPill, { status: s.status }) }), _jsxs("td", { children: [_jsx(SeverityBar, { counts: s.summary }), _jsxs("p", { className: "mt-1 font-mono text-[11px] text-ink-muted", children: [s.summary.critical ?? 0, "C \u00B7 ", s.summary.high ?? 0, "H \u00B7 ", s.summary.medium ?? 0, "M \u00B7 ", s.summary.low ?? 0, "L"] })] }), _jsx("td", { className: "text-xs text-ink-muted", children: formatDate(s.completed_at) })] }, s.id))) })] }) }));
}
function ImageMeta({ scanId }) {
    const scan = useScan(scanId);
    const image = (scan.data?.metadata?.image ?? null);
    const os = scan.data?.metadata?.os;
    if (!scan.data)
        return _jsx(Loading, {});
    return (_jsxs("dl", { className: "grid gap-3 text-xs sm:grid-cols-4", children: [_jsxs("div", { children: [_jsx("dt", { className: "text-ink-faint", children: "Image" }), _jsx("dd", { className: "font-mono", children: scan.data.target })] }), _jsxs("div", { children: [_jsx("dt", { className: "text-ink-faint", children: "Digest" }), _jsxs("dd", { className: "truncate font-mono", title: String(image?.digest ?? ""), children: [String(image?.digest ?? "—").slice(0, 24), "\u2026"] })] }), _jsxs("div", { children: [_jsx("dt", { className: "text-ink-faint", children: "OS" }), _jsx("dd", { children: os ?? "—" })] }), _jsxs("div", { children: [_jsx("dt", { className: "text-ink-faint", children: "Scanner" }), _jsxs("dd", { children: ["Trivy (", scan.data.adapter_mode, ")"] })] })] }));
}
export function ContainerScansPage() {
    const scans = useScans({ scan_type: "container", limit: 100 });
    const [selected, setSelected] = useState(null);
    const completed = (scans.data ?? []).filter((s) => s.status === "completed");
    const latest = selected ?? completed[0]?.id ?? null;
    return (_jsxs("div", { className: "space-y-6", children: [_jsx(PageHeader, { title: "Container scans", subtitle: "Trivy image scans of registered container images (OS and language packages)." }), _jsxs(Card, { title: "Scan history", children: [scans.isLoading && _jsx(Loading, {}), scans.error && _jsx(ErrorState, { error: scans.error }), scans.data && _jsx(ScanHistory, { scans: scans.data, selected: latest, onSelect: setSelected })] }), latest !== null && (_jsxs(Card, { title: `Scan #${latest} details`, children: [_jsx(ImageMeta, { scanId: latest }), _jsx("div", { className: "mt-5", children: _jsx(FindingsTableForScan, { scanId: latest }) })] }))] }));
}
function FindingsTableForScan({ scanId }) {
    const findings = useFindings({ scan_id: scanId, limit: 200 });
    if (findings.isLoading)
        return _jsx(Loading, {});
    if (!findings.data || findings.data.items.length === 0)
        return _jsx(EmptyState, { title: "No vulnerabilities in this image" });
    return (_jsx("div", { className: "overflow-x-auto", children: _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Severity" }), _jsx("th", { children: "CVE" }), _jsx("th", { children: "Package" }), _jsx("th", { children: "Installed" }), _jsx("th", { children: "Fixed" }), _jsx("th", { children: "Title" })] }) }), _jsx("tbody", { children: findings.data.items.map((f) => (_jsxs("tr", { children: [_jsx("td", { children: _jsx(SeverityBadge, { severity: f.severity }) }), _jsx("td", { className: "font-mono text-xs", children: f.reference_url ? _jsx("a", { className: "hover:text-brand", href: f.reference_url, target: "_blank", rel: "noreferrer noopener", children: f.rule_id }) : f.rule_id }), _jsx("td", { className: "font-mono text-xs", children: f.component }), _jsx("td", { className: "font-mono text-xs text-ink-muted", children: f.installed_version }), _jsx("td", { className: "font-mono text-xs text-ok", children: f.fixed_version ?? _jsx("span", { className: "text-ink-faint", children: "\u2014" }) }), _jsx("td", { className: "max-w-md text-sm", children: f.title })] }, f.id))) })] }) }));
}
export function DependencyScansPage() {
    const scans = useScans({ scan_type: "dependency", limit: 100 });
    const [vulnerableOnly, setVulnerableOnly] = useState(false);
    const inventory = useDependencies({ vulnerable_only: vulnerableOnly });
    return (_jsxs("div", { className: "space-y-6", children: [_jsx(PageHeader, { title: "Dependency scans", subtitle: "pip-audit results, dependency inventory and vulnerable packages." }), _jsxs("div", { className: "grid gap-4 xl:grid-cols-2", children: [_jsxs(Card, { title: "Scan history", children: [scans.isLoading && _jsx(Loading, {}), scans.data && _jsx(ScanHistory, { scans: scans.data, selected: null, onSelect: () => undefined })] }), _jsxs(Card, { title: "Dependency inventory", action: _jsxs("label", { className: "flex items-center gap-2 text-xs text-ink-muted", children: [_jsx("input", { type: "checkbox", checked: vulnerableOnly, onChange: (e) => setVulnerableOnly(e.target.checked) }), " Vulnerable only"] }), children: [inventory.isLoading && _jsx(Loading, {}), inventory.data && inventory.data.length === 0 && _jsx(EmptyState, { title: "No dependencies recorded" }), inventory.data && inventory.data.length > 0 && (_jsx("div", { className: "max-h-96 overflow-auto", children: _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Package" }), _jsx("th", { children: "Version" }), _jsx("th", { children: "Project" }), _jsx("th", { children: "Vulns" })] }) }), _jsx("tbody", { children: inventory.data.map((d) => (_jsxs("tr", { children: [_jsx("td", { className: "font-mono text-xs", children: d.name }), _jsx("td", { className: "font-mono text-xs", children: d.version }), _jsx("td", { className: "text-xs text-ink-muted", children: d.project_name }), _jsx("td", { children: d.vulnerable ? _jsx("span", { className: "font-mono text-xs text-sev-high", children: d.vulnerability_count }) : _jsx("span", { className: "text-xs text-ok", children: "clean" }) })] }, d.id))) })] }) }))] })] }), _jsx(Card, { title: "Vulnerable dependencies", children: _jsx(FindingsTable, { category: "dependency" }) })] }));
}
