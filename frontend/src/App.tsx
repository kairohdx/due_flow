import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { useAuthBootstrap } from "./auth/useAuthBootstrap";
import { AppShell } from "./components/AppShell";
import { FoundationPage } from "./pages/FoundationPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CustomerCreatePage } from "./pages/CustomerCreatePage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { CustomersPage } from "./pages/CustomersPage";
import { ChargeCreatePage } from "./pages/ChargeCreatePage";
import { ChargeDetailPage } from "./pages/ChargeDetailPage";
import { ChargesPage } from "./pages/ChargesPage";
import { ExecutionDetailPage } from "./pages/ExecutionDetailPage";
import { ExecutionsPage } from "./pages/ExecutionsPage";
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
        <Route index element={<DashboardPage />} />
        <Route path="clientes" element={<CustomersPage />} />
        <Route path="clientes/novo" element={<CustomerCreatePage />} />
        <Route path="clientes/:customerId" element={<CustomerDetailPage />} />
        <Route path="cobrancas" element={<ChargesPage />} />
        <Route path="cobrancas/nova" element={<ChargeCreatePage />} />
        <Route path="cobrancas/:chargeId" element={<ChargeDetailPage />} />
        <Route path="fila" element={<ExecutionsPage />} />
        <Route path="fila/:executionId" element={<ExecutionDetailPage />} />
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
