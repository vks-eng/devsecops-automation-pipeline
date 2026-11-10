import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedLayout } from "./components/Layout";
import CodeQualityPage from "./pages/CodeQuality";
import DashboardPage from "./pages/Dashboard";
import LoginPage from "./pages/Login";
import NotificationsPage from "./pages/Notifications";
import PipelinesPage from "./pages/Pipelines";
import ProjectDetailPage from "./pages/ProjectDetail";
import ProjectsPage from "./pages/Projects";
import ReportsPage from "./pages/Reports";
import { ContainerScansPage, DependencyScansPage } from "./pages/ScanPages";
import SettingsPage from "./pages/Settings";
import VulnerabilitiesPage from "./pages/Vulnerabilities";
export default function App() {
    return (_jsxs(Routes, { children: [_jsx(Route, { path: "/login", element: _jsx(LoginPage, {}) }), _jsxs(Route, { element: _jsx(ProtectedLayout, {}), children: [_jsx(Route, { index: true, element: _jsx(DashboardPage, {}) }), _jsx(Route, { path: "projects", element: _jsx(ProjectsPage, {}) }), _jsx(Route, { path: "projects/:id", element: _jsx(ProjectDetailPage, {}) }), _jsx(Route, { path: "pipelines", element: _jsx(PipelinesPage, {}) }), _jsx(Route, { path: "code-quality", element: _jsx(CodeQualityPage, {}) }), _jsx(Route, { path: "vulnerabilities", element: _jsx(VulnerabilitiesPage, {}) }), _jsx(Route, { path: "containers", element: _jsx(ContainerScansPage, {}) }), _jsx(Route, { path: "dependencies", element: _jsx(DependencyScansPage, {}) }), _jsx(Route, { path: "reports", element: _jsx(ReportsPage, {}) }), _jsx(Route, { path: "notifications", element: _jsx(NotificationsPage, {}) }), _jsx(Route, { path: "settings", element: _jsx(SettingsPage, {}) })] }), _jsx(Route, { path: "*", element: _jsx(Navigate, { to: "/", replace: true }) })] }));
}
