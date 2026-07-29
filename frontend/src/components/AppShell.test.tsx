import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as dashboardApi from "../api/dashboard";
import {
  markAuthInitialized,
  resetAuthStateForTests,
  setAuthSession,
} from "../auth/authStore";
import { AppShell } from "./AppShell";

vi.mock("../api/dashboard", () => ({
  getAutomation: vi.fn(),
}));
vi.mock("../auth/authService", () => ({
  logout: vi.fn(),
}));

beforeEach(() => {
  resetAuthStateForTests();
  markAuthInitialized();
  setAuthSession("access-token-for-test", {
    id: "user-1",
    email: "admin@example.com",
    name: "Administrador",
  });
  vi.mocked(dashboardApi.getAutomation).mockResolvedValue({
    enabled: true,
    interval_seconds: 120,
    last_enqueued_at: null,
    next_run_at: "2026-07-29T12:02:00Z",
    updated_at: "2026-07-29T12:00:00Z",
  });
});

it("expõe atalhos funcionais e o estado real da automação", async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<div>Visão geral</div>} />
            <Route path="notificacoes" element={<div>Tela do histórico</div>} />
            <Route path="configuracoes" element={<div>Tela de configurações</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Ativa")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Automação: ativa" }),
  ).toHaveAttribute("href", "/configuracoes");
  expect(
    screen.getByRole("link", { name: "Ir para o conteúdo principal" }),
  ).toHaveAttribute("href", "#conteudo-principal");

  await user.click(
    screen.getByRole("button", { name: "Abrir histórico de mensagens" }),
  );
  expect(await screen.findByText("Tela do histórico")).toBeInTheDocument();
});
