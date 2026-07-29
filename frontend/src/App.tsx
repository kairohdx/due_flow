import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { useAuthBootstrap } from "./auth/useAuthBootstrap";
import { AppShell } from "./components/AppShell";
import { FoundationPage } from "./pages/FoundationPage";
import { LoginPage } from "./pages/LoginPage";

export default function App() {
  useAuthBootstrap();
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<FoundationPage type="dashboard" />} />
        <Route path="clientes" element={<FoundationPage type="customers" />} />
        <Route path="cobrancas" element={<FoundationPage type="charges" />} />
        <Route path="fila" element={<FoundationPage type="jobs" />} />
        <Route
          path="notificacoes"
          element={<FoundationPage type="notifications" />}
        />
        <Route
          path="configuracoes"
          element={<FoundationPage type="settings" />}
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
