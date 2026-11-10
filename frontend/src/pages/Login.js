import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Lock, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Brand } from "../components/Layout";
import { useAuth } from "../lib/auth";
export default function LoginPage() {
    const { user, login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const from = location.state?.from ?? "/";
    if (user)
        return _jsx(Navigate, { to: from, replace: true });
    async function onSubmit(event) {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
            await login(email, password);
            navigate(from, { replace: true });
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
        }
        finally {
            setBusy(false);
        }
    }
    return (_jsxs("div", { className: "grid min-h-full lg:grid-cols-[1.1fr_1fr]", children: [_jsxs("section", { className: "relative hidden overflow-hidden border-r border-line bg-surface/60 p-12 lg:flex lg:flex-col lg:justify-between", children: [_jsx(Brand, {}), _jsxs("div", { className: "max-w-lg", children: [_jsxs("h1", { className: "text-4xl font-semibold leading-tight tracking-tight", children: ["Security posture for every project, ", _jsx("span", { className: "text-brand", children: "in one place." })] }), _jsx("p", { className: "mt-4 text-ink-muted", children: "ShieldOps aggregates SonarQube, Trivy, pip-audit and GitHub Actions results into one security score, with trends, remediation guidance and alerts." }), _jsx("ul", { className: "mt-8 grid grid-cols-2 gap-3 text-sm text-ink-muted", children: ["Code quality gates", "Container CVEs", "Dependency audits", "CI/CD health"].map((item) => (_jsxs("li", { className: "flex items-center gap-2", children: [_jsx(ShieldCheck, { size: 16, className: "text-brand", "aria-hidden": true }), " ", item] }, item))) })] }), _jsx("p", { className: "text-xs text-ink-faint", children: "Integrations run in mock mode by default. No credentials required." })] }), _jsx("section", { className: "flex items-center justify-center p-6", children: _jsxs("form", { onSubmit: onSubmit, className: "card w-full max-w-sm p-8", "aria-labelledby": "login-title", children: [_jsx("div", { className: "mb-6 lg:hidden", children: _jsx(Brand, {}) }), _jsx("h2", { id: "login-title", className: "text-xl font-semibold", children: "Sign in" }), _jsx("p", { className: "mt-1 text-sm text-ink-muted", children: "Use your ShieldOps account." }), _jsxs("div", { className: "mt-6 space-y-4", children: [_jsxs("label", { className: "block", children: [_jsx("span", { className: "label", children: "Email" }), _jsx("input", { className: "input", type: "email", autoComplete: "username", required: true, value: email, onChange: (e) => setEmail(e.target.value) })] }), _jsxs("label", { className: "block", children: [_jsx("span", { className: "label", children: "Password" }), _jsx("input", { className: "input", type: "password", autoComplete: "current-password", required: true, value: password, onChange: (e) => setPassword(e.target.value) })] })] }), error && (_jsx("p", { role: "alert", className: "mt-4 rounded-md border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad", children: error })), _jsxs("button", { type: "submit", className: "btn-primary mt-6 w-full justify-center", disabled: busy, children: [_jsx(Lock, { size: 15, "aria-hidden": true }), " ", busy ? "Signing in…" : "Sign in"] }), _jsxs("p", { className: "mt-4 text-center text-xs text-ink-faint", children: ["Local demo: run ", _jsx("code", { className: "font-mono", children: "python -m app.seed" }), " (see README)."] })] }) })] }));
}
