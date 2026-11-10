import { FolderGit2, Plus, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Card, EmptyState, ErrorState, GradeBadge, Loading, PageHeader, SeverityBar, StatusPill } from "../components/ui";
import { relativeTime } from "../lib/format";
import { useCreateProject, useDashboard, useProjects } from "../lib/queries";
import { validateRepoUrl } from "../lib/validation";

const splitList = (value: string) =>
  value
    .split(/[\n,]/)
    .map((v) => v.trim())
    .filter(Boolean);

function CreateProjectForm({ onDone }: { onDone: () => void }) {
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
  const [clientError, setClientError] = useState<string | null>(null);
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e: FormEvent) {
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

  return (
    <Card title="Register project" action={<button type="button" aria-label="Close" onClick={onDone} className="text-ink-muted hover:text-ink"><X size={16} /></button>}>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <label>
          <span className="label">Name</span>
          <input className="input" required minLength={2} value={form.name} onChange={set("name")} />
        </label>
        <label>
          <span className="label">GitHub repository URL</span>
          <input className="input" required placeholder="https://github.com/owner/repo" value={form.repo_url} onChange={set("repo_url")} />
        </label>
        <label>
          <span className="label">Team</span>
          <input className="input" value={form.team} onChange={set("team")} />
        </label>
        <label>
          <span className="label">Default branch</span>
          <input className="input" value={form.default_branch} onChange={set("default_branch")} />
        </label>
        <label>
          <span className="label">Additional branches (comma separated)</span>
          <input className="input" placeholder="develop, release/2.x" value={form.branches} onChange={set("branches")} />
        </label>
        <label>
          <span className="label">SonarQube project key</span>
          <input className="input" placeholder="org_project" value={form.sonar_project_key} onChange={set("sonar_project_key")} />
        </label>
        <label className="md:col-span-2">
          <span className="label">Container images (one per line)</span>
          <textarea className="input min-h-20 font-mono" placeholder="ghcr.io/org/app:1.0.0" value={form.container_images} onChange={set("container_images")} />
        </label>
        {(clientError || create.error) && (
          <div className="md:col-span-2">
            <ErrorState error={clientError ? new Error(clientError) : create.error} />
          </div>
        )}
        <div className="md:col-span-2">
          <button type="submit" className="btn-primary" disabled={create.isPending}>
            <Plus size={15} aria-hidden /> {create.isPending ? "Registering…" : "Register project"}
          </button>
        </div>
      </form>
    </Card>
  );
}

export default function ProjectsPage() {
  const projects = useProjects();
  const dashboard = useDashboard();
  const [creating, setCreating] = useState(false);
  const overview = new Map((dashboard.data?.projects ?? []).map((p) => [p.project_id, p]));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        subtitle="Registered repositories, their configuration and security posture."
        actions={
          <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
            <Plus size={15} aria-hidden /> New project
          </button>
        }
      />
      {creating && <CreateProjectForm onDone={() => setCreating(false)} />}
      {projects.isLoading && <Loading />}
      {projects.error && <ErrorState error={projects.error} />}
      {projects.data && projects.data.length === 0 && (
        <Card>
          <EmptyState title="No projects registered">Use “New project” to register a GitHub repository.</EmptyState>
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {projects.data?.map((p) => {
          const o = overview.get(p.id);
          return (
            <Link key={p.id} to={`/projects/${p.id}`} className="card group block p-5 transition-colors hover:border-brand/50">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 font-semibold group-hover:text-brand">
                    <FolderGit2 size={16} aria-hidden /> {p.name}
                  </p>
                  <p className="mt-0.5 truncate font-mono text-xs text-ink-faint">
                    {p.repo_owner}/{p.repo_name}
                  </p>
                </div>
                {o && <GradeBadge grade={o.grade} score={o.score} />}
              </div>
              <p className="mt-3 line-clamp-2 min-h-10 text-sm text-ink-muted">{p.description || "No description"}</p>
              {o && (
                <div className="mt-4">
                  <SeverityBar counts={o.counts} />
                </div>
              )}
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
                <span className="rounded bg-surface-3 px-1.5 py-0.5">{p.team || "No team"}</span>
                <span className="rounded bg-surface-3 px-1.5 py-0.5 font-mono">{p.default_branch}</span>
                <span className="rounded bg-surface-3 px-1.5 py-0.5">{p.container_images.length} images</span>
                {o && <StatusPill status={o.quality_gate_status} />}
                <span className="ml-auto">{o ? `scanned ${relativeTime(o.last_scan_at)}` : ""}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
