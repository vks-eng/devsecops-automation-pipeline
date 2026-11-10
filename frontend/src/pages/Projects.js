import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { FolderGit2, Plus, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, EmptyState, ErrorState, GradeBadge, Loading, PageHeader, SeverityBar, StatusPill } from "../components/ui";
import { relativeTime } from "../lib/format";
import { useCreateProject, useDashboard, useProjects } from "../lib/queries";
import { validateRepoUrl } from "../lib/validation";
const splitList = (value) => value
    .split(/[\n,]/)
    .map((v) => v.trim())
    .filter(Boolean);
function CreateProjectForm({ onDone }) {
    const create = useCreateProject();
    const [form, setForm] = useState({
        name: "",
        repo_url: "",
        team: "",
        default_branch: "main",
        branches: "",
        sonar_project_key: "",
        container_images: "",
    });
    const [clientError, setClientError] = useState(null);
    const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
    async function submit(e) {
        e.preventDefault();
        const repoError = validateRepoUrl(form.repo_url.trim());
        if (repoError) {
            setClientError(repoError);
            return;
        }
        setClientError(null);
        await create.mutateAsync({
            name: form.name.trim(),
            repo_url: form.repo_url.trim(),
            team: form.team.trim(),
            default_branch: form.default_branch.trim() || "main",
            branches: splitList(form.branches),
            sonar_project_key: form.sonar_project_key.trim() || null,
            container_images: splitList(form.container_images),
        });
        onDone();
    }
    return (_jsx(Card, { title: "Register project", action: _jsx("button", { type: "button", "aria-label": "Close", onClick: onDone, className: "text-ink-muted hover:text-ink", children: _jsx(X, { size: 16 }) }), children: _jsxs("form", { onSubmit: submit, className: "grid gap-4 md:grid-cols-2", children: [_jsxs("label", { children: [_jsx("span", { className: "label", children: "Name" }), _jsx("input", { className: "input", required: true, minLength: 2, value: form.name, onChange: set("name") })] }), _jsxs("label", { children: [_jsx("span", { className: "label", children: "GitHub repository URL" }), _jsx("input", { className: "input", required: true, placeholder: "https://github.com/owner/repo", value: form.repo_url, onChange: set("repo_url") })] }), _jsxs("label", { children: [_jsx("span", { className: "label", children: "Team" }), _jsx("input", { className: "input", value: form.team, onChange: set("team") })] }), _jsxs("label", { children: [_jsx("span", { className: "label", children: "Default branch" }), _jsx("input", { className: "input", value: form.default_branch, onChange: set("default_branch") })] }), _jsxs("label", { children: [_jsx("span", { className: "label", children: "Additional branches (comma separated)" }), _jsx("input", { className: "input", placeholder: "develop, release/2.x", value: form.branches, onChange: set("branches") })] }), _jsxs("label", { children: [_jsx("span", { className: "label", children: "SonarQube project key" }), _jsx("input", { className: "input", placeholder: "org_project", value: form.sonar_project_key, onChange: set("sonar_project_key") })] }), _jsxs("label", { className: "md:col-span-2", children: [_jsx("span", { className: "label", children: "Container images (one per line)" }), _jsx("textarea", { className: "input min-h-20 font-mono", placeholder: "ghcr.io/org/app:1.0.0", value: form.container_images, onChange: set("container_images") })] }), (clientError || create.error) && (_jsx("div", { className: "md:col-span-2", children: _jsx(ErrorState, { error: clientError ? new Error(clientError) : create.error }) })), _jsx("div", { className: "md:col-span-2", children: _jsxs("button", { type: "submit", className: "btn-primary", disabled: create.isPending, children: [_jsx(Plus, { size: 15, "aria-hidden": true }), " ", create.isPending ? "Registering…" : "Register project"] }) })] }) }));
}
export default function ProjectsPage() {
    const projects = useProjects();
    const dashboard = useDashboard();
    const [creating, setCreating] = useState(false);
    const overview = new Map((dashboard.data?.projects ?? []).map((p) => [p.project_id, p]));
    return (_jsxs("div", { className: "space-y-6", children: [_jsx(PageHeader, { title: "Projects", subtitle: "Registered repositories, their configuration and security posture.", actions: _jsxs("button", { type: "button", className: "btn-primary", onClick: () => setCreating(true), children: [_jsx(Plus, { size: 15, "aria-hidden": true }), " New project"] }) }), creating && _jsx(CreateProjectForm, { onDone: () => setCreating(false) }), projects.isLoading && _jsx(Loading, {}), projects.error && _jsx(ErrorState, { error: projects.error }), projects.data && projects.data.length === 0 && (_jsx(Card, { children: _jsx(EmptyState, { title: "No projects registered", children: "Use \u201CNew project\u201D to register a GitHub repository." }) })), _jsx("div", { className: "grid gap-4 md:grid-cols-2 xl:grid-cols-3", children: projects.data?.map((p) => {
                    const o = overview.get(p.id);
                    return (_jsxs(Link, { to: `/projects/${p.id}`, className: "card group block p-5 transition-colors hover:border-brand/50", children: [_jsxs("div", { className: "flex items-start justify-between gap-3", children: [_jsxs("div", { className: "min-w-0", children: [_jsxs("p", { className: "flex items-center gap-2 font-semibold group-hover:text-brand", children: [_jsx(FolderGit2, { size: 16, "aria-hidden": true }), " ", p.name] }), _jsxs("p", { className: "mt-0.5 truncate font-mono text-xs text-ink-faint", children: [p.repo_owner, "/", p.repo_name] })] }), o && _jsx(GradeBadge, { grade: o.grade, score: o.score })] }), _jsx("p", { className: "mt-3 line-clamp-2 min-h-10 text-sm text-ink-muted", children: p.description || "No description" }), o && (_jsx("div", { className: "mt-4", children: _jsx(SeverityBar, { counts: o.counts }) })), _jsxs("div", { className: "mt-4 flex flex-wrap items-center gap-2 text-xs text-ink-muted", children: [_jsx("span", { className: "rounded bg-surface-3 px-1.5 py-0.5", children: p.team || "No team" }), _jsx("span", { className: "rounded bg-surface-3 px-1.5 py-0.5 font-mono", children: p.default_branch }), _jsxs("span", { className: "rounded bg-surface-3 px-1.5 py-0.5", children: [p.container_images.length, " images"] }), o && _jsx(StatusPill, { status: o.quality_gate_status }), _jsx("span", { className: "ml-auto", children: o ? `scanned ${relativeTime(o.last_scan_at)}` : "" })] })] }, p.id));
                }) })] }));
}
