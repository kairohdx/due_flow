import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as dashboardApi from "../api/dashboard";
import * as settingsApi from "../api/settings";
import {
  markAuthInitialized,
  resetAuthStateForTests,
  setAuthSession,
} from "../auth/authStore";
import { SettingsPage } from "./SettingsPage";

vi.mock("../api/dashboard", () => ({
  getAutomation: vi.fn(),
  configureAutomation: vi.fn(),
  enableAutomation: vi.fn(),
  disableAutomation: vi.fn(),
}));

vi.mock("../api/settings", () => ({
  changePassword: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/configuracoes"]}>
        <Routes>
          <Route path="/configuracoes" element={<SettingsPage />} />
          <Route path="/login" element={<div>Login após senha alterada</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  resetAuthStateForTests();
  markAuthInitialized();
  setAuthSession("token", {
    id: "user-1",
    name: "Administrador",
    email: "admin@example.com",
  });
  vi.mocked(dashboardApi.getAutomation).mockResolvedValue({
    enabled: false,
    interval_seconds: 120,
    last_enqueued_at: null,
    next_run_at: null,
    updated_at: "2026-07-29T12:00:00Z",
  });
  vi.mocked(dashboardApi.configureAutomation).mockResolvedValue({
    enabled: false,
    interval_seconds: 300,
    last_enqueued_at: null,
    next_run_at: null,
    updated_at: "2026-07-29T12:01:00Z",
  });
  vi.mocked(dashboardApi.enableAutomation).mockResolvedValue({
    enabled: true,
    interval_seconds: 120,
    last_enqueued_at: null,
    next_run_at: "2026-07-29T12:02:00Z",
    updated_at: "2026-07-29T12:00:00Z",
  });
  vi.mocked(settingsApi.changePassword).mockResolvedValue(undefined);
});

afterEach(() => {
  vi.clearAllMocks();
});

it("exibe a conta e permite configurar e ativar a automação", async () => {
  const user = userEvent.setup();
  renderPage();

  expect(await screen.findByText("Administrador")).toBeInTheDocument();
  expect(await screen.findByText("Automação pausada")).toBeInTheDocument();

  const interval = screen.getByLabelText("Intervalo em minutos");
  await user.clear(interval);
  await user.type(interval, "5");
  await user.click(screen.getByRole("button", { name: "Salvar intervalo" }));
  await waitFor(() =>
    expect(dashboardApi.configureAutomation).toHaveBeenCalledWith(300),
  );

  await user.click(screen.getByRole("button", { name: "Ativar automação" }));
  await waitFor(() =>
    expect(dashboardApi.enableAutomation).toHaveBeenCalledOnce(),
  );
});

it("altera a senha, encerra a sessão e direciona para o login", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByText("Segurança");
  await user.type(screen.getByLabelText("Senha atual"), "senha-antiga");
  await user.type(screen.getByLabelText("Nova senha"), "senha-nova-123");
  await user.type(
    screen.getByLabelText("Confirmar nova senha"),
    "senha-nova-123",
  );
  await user.click(screen.getByRole("button", { name: "Alterar senha" }));

  await waitFor(() =>
    expect(settingsApi.changePassword).toHaveBeenCalledWith({
      current_password: "senha-antiga",
      new_password: "senha-nova-123",
    }),
  );
  expect(await screen.findByText("Login após senha alterada")).toBeInTheDocument();
});
