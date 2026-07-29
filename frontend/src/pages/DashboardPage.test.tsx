import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { markAuthInitialized, setAuthSession } from "../auth/authStore";
import type { Job } from "../api/types";
import * as dashboardApi from "../api/dashboard";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/dashboard", () => ({
  getDashboardSummary: vi.fn(),
  getAutomation: vi.fn(),
  enableAutomation: vi.fn(),
  disableAutomation: vi.fn(),
  enqueueProcessing: vi.fn(),
  getRecentJobs: vi.fn(),
  getJob: vi.fn(),
}));

const completedJob: Job = {
  id: "job-1",
  type: "process_due_charges",
  status: "completed",
  origin: "manual",
  charge_id: null,
  terminal: true,
  duration_ms: 420,
  payload: { origin: "manual" },
  result: {
    evaluated: 3,
    eligible: 2,
    skipped: 1,
    simulated: 2,
    deduplicated: 0,
    notification_failed: 0,
  },
  scheduled_for: "2026-07-29T12:00:00Z",
  attempts: 1,
  max_attempts: 3,
  started_at: "2026-07-29T12:00:00Z",
  finished_at: "2026-07-29T12:00:00.420Z",
  error: null,
  retain_deduplication_key: true,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-29T12:00:00.420Z",
};

function configureApi() {
  vi.mocked(dashboardApi.getDashboardSummary).mockResolvedValue({
    generated_at: "2026-07-29T12:00:00Z",
    window_started_at: "2026-07-28T12:00:00Z",
    customers_total: 18,
    charges_pending: 9,
    charges_overdue: 3,
    charges_due_today: 2,
    charges_due_next_7_days: 4,
    charges_evaluated_last_24h: 27,
    submissions_succeeded_last_24h: 12,
    submissions_failed_last_24h: 1,
    submissions_unknown_last_24h: 0,
    deliveries_confirmed_last_24h: 10,
    deliveries_read_last_24h: 4,
    deliveries_failed_last_24h: 1,
    deliveries_awaiting: 1,
    jobs_queued: 2,
    jobs_processing: 1,
    jobs_completed_last_24h: 12,
    job_retries_last_24h: 3,
    jobs_failed_last_24h: 1,
  });
  vi.mocked(dashboardApi.getAutomation).mockResolvedValue({
    enabled: false,
    interval_seconds: 120,
    last_enqueued_at: null,
    next_run_at: null,
    updated_at: "2026-07-29T12:00:00Z",
  });
  vi.mocked(dashboardApi.getRecentJobs).mockResolvedValue({
    items: [completedJob],
    page: 1,
    page_size: 5,
    total: 1,
    pages: 1,
  });
  vi.mocked(dashboardApi.getJob).mockResolvedValue(completedJob);
  vi.mocked(dashboardApi.enqueueProcessing).mockResolvedValue({
    job_id: "job-1",
    status: "queued",
    created: true,
  });
  vi.mocked(dashboardApi.enableAutomation).mockResolvedValue({
    enabled: true,
    interval_seconds: 120,
    last_enqueued_at: null,
    next_run_at: "2026-07-29T12:02:00Z",
    updated_at: "2026-07-29T12:00:00Z",
  });
}

function renderDashboard() {
  setAuthSession("token", {
    id: "user-1",
    email: "admin@example.com",
    name: "Maria Silva",
  });
  markAuthInitialized();
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  configureApi();
});

it("apresenta métricas, automação e atividade recente", async () => {
  renderDashboard();

  expect(await screen.findByText("Olá, Maria.")).toBeInTheDocument();
  expect(await screen.findByText("18")).toBeInTheDocument();
  expect(screen.getByText("Clientes cadastrados")).toBeInTheDocument();
  expect(screen.getByText("Cobranças em aberto")).toBeInTheDocument();
  expect(screen.getAllByText("Cobranças vencidas")).toHaveLength(2);
  expect(screen.getAllByText("Vencem hoje")).toHaveLength(2);
  expect(screen.getByText("Vencem em até 7 dias")).toBeInTheDocument();
  expect(screen.getByText("Envios aceitos pela Meta")).toBeInTheDocument();
  expect(screen.getByText("Falhas ao enviar para a Meta")).toBeInTheDocument();
  expect(screen.getByText("Atenção necessária")).toBeInTheDocument();
  expect(screen.queryByText("Retries")).not.toBeInTheDocument();
  expect(screen.queryByText("Processamento manual")).not.toBeInTheDocument();
  expect(screen.getByText("Pausada")).toBeInTheDocument();
});

it("habilita a automação pela tela", async () => {
  const user = userEvent.setup();
  renderDashboard();

  await user.click(await screen.findByRole("button", { name: "Ativar automação" }));

  expect(dashboardApi.enableAutomation).toHaveBeenCalledOnce();
  expect(await screen.findByText("Ativa")).toBeInTheDocument();
});

it("acompanha a verificação manual até o estado terminal", async () => {
  const user = userEvent.setup();
  renderDashboard();

  await user.click(await screen.findByRole("button", { name: "Verificar agora" }));

  expect(dashboardApi.enqueueProcessing).toHaveBeenCalledOnce();
  expect(await screen.findByText("Verificação concluída")).toBeInTheDocument();
  expect(screen.getByText(/2 mensagem\(ns\) enviada\(s\)/)).toBeInTheDocument();
});
