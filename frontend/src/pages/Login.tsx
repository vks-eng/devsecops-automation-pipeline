import { Lock, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Brand } from "../components/Layout";
import { useAuth } from "../lib/auth";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (user) return <Navigate to={from} replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden border-r border-line bg-surface/60 p-12 lg:flex lg:flex-col lg:justify-between">
        <Brand />
        <div className="max-w-lg">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">
            Security posture for every project, <span className="text-brand">in one place.</span>
          </h1>
          <p className="mt-4 text-ink-muted">
            ShieldOps aggregates SonarQube, Trivy, pip-audit and GitHub Actions results into one security score, with
            trends, remediation guidance and alerts.
          </p>
          <ul className="mt-8 grid grid-cols-2 gap-3 text-sm text-ink-muted">
            {["Code quality gates", "Container CVEs", "Dependency audits", "CI/CD health"].map((item) => (
              <li key={item} className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-brand" aria-hidden /> {item}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-ink-faint">Integrations run in mock mode by default. No credentials required.</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <form onSubmit={onSubmit} className="card w-full max-w-sm p-8" aria-labelledby="login-title">
          <div className="mb-6 lg:hidden">
            <Brand />
          </div>
          <h2 id="login-title" className="text-xl font-semibold">
            Sign in
          </h2>
          <p className="mt-1 text-sm text-ink-muted">Use your ShieldOps account.</p>
          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="label">Email</span>
              <input
                className="input"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="label">Password</span>
              <input
                className="input"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
          </div>
          {error && (
            <p role="alert" className="mt-4 rounded-md border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
              {error}
            </p>
          )}
          <button type="submit" className="btn-primary mt-6 w-full justify-center" disabled={busy}>
            <Lock size={15} aria-hidden /> {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="mt-4 text-center text-xs text-ink-faint">
            Local demo: run <code className="font-mono">python -m app.seed</code> (see README).
          </p>
        </form>
      </section>
    </div>
  );
}
