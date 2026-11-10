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
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id" element={<ProjectDetailPage />} />
        <Route path="pipelines" element={<PipelinesPage />} />
        <Route path="code-quality" element={<CodeQualityPage />} />
        <Route path="vulnerabilities" element={<VulnerabilitiesPage />} />
        <Route path="containers" element={<ContainerScansPage />} />
        <Route path="dependencies" element={<DependencyScansPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
