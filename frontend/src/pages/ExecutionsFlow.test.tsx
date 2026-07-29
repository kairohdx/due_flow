import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as executionsApi from "../api/executions";
import type { Job } from "../api/types";
import { ExecutionDetailPage } from "./ExecutionDetailPage";
import { ExecutionsPage } from "./ExecutionsPage";

vi.mock("../api/executions", () => ({
  getExecutions: vi.fn(),
  getExecution: vi.fn(),
}));

const completedExecution: Job = {
  id: "11111111-1111-1111-1111-111111111111",
  type: "process_charge",
  status: "completed",
  origin: "manual",
  charge_id: "22222222-2222-2222-2222-222222222222",
  terminal: true,
  duration_ms: 420,
  payload: {
    origin: "manual",
    charge_id: "22222222-2222-2222-2222-222222222222",
  },
  result: {
    reference_date: "2026-07-29",
    evaluated: 1,
    eligible: 1,
    skipped: 0,
    simulated: 1,
    deduplicated: 0,
    notification_failed: 0,
    evaluations: [
      {
        charge_id: "22222222-2222-2222-2222-222222222222",
        decision: {
          decision: "notify",
          notification_type: "due_today",
          template_key: "charge_due_today",
          reason: "charge_is_due_today",
          eligible: true,
          recommended_action: "send",
          policy_name: "DueTodayPolicy",
          metadata: { days_until_due: 0 },
        },
        trace: {
          trace_id: "trace-1",
          execution_id: "policy-execution-1",
          pipeline: "charge_notification",
          strategy: "FirstMatch",
          status: "completed",
          duration_ms: 2.4,
          selected_policy: "DueTodayPolicy",
          evaluated: [
            {
              policy_name: "SkipInactiveCustomerPolicy",
              matched: false,
              outcome: "pass",
              reason: "customer_is_active",
              duration_ms: 0.2,
            },
            {
              policy_name: "DueTodayPolicy",
              matched: true,
              outcome: "consume",
              reason: "charge_is_due_today",
              duration_ms: 0.4,
            },
          ],
          not_evaluated: ["UpcomingReminderPolicy", "NoNotificationPolicy"],
        },
        notification: {
          attempt_id: "33333333-3333-3333-3333-333333333333",
          status: "simulated",
          provider_message_id: "fake-1",
          idempotency_key: "dedup-key",
          deduplicated: false,
          error: null,
        },
      },
    ],
  },
  scheduled_for: "2026-07-29T12:00:00Z",
  attempts: 1,
  max_attempts: 3,
  locked_at: "2026-07-29T12:00:00Z",
  locked_by: "worker-local",
  started_at: "2026-07-29T12:00:00Z",
  finished_at: "2026-07-29T12:00:00.420Z",
  error: null,
  retain_deduplication_key: true,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-29T12:00:00.420Z",
};

function wrapper(initialEntry: string, routes: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>{routes}</Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(executionsApi.getExecutions).mockResolvedValue({
    items: [completedExecution],
    page: 1,
    page_size: 25,
    total: 26,
    pages: 2,
  });
  vi.mocked(executionsApi.getExecution).mockResolvedValue(completedExecution);
});

it("lista execuções e mantém os filtros e a paginação na URL", async () => {
  const user = userEvent.setup();
  wrapper("/fila", <Route path="/fila" element={<ExecutionsPage />} />);

  expect(await screen.findByText("Cobrança individual")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Filtrar estado"), "completed");
  await user.selectOptions(screen.getByLabelText("Filtrar origem"), "manual");
  await waitFor(() =>
    expect(executionsApi.getExecutions).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "completed", origin: "manual", page: 1 }),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Próxima página" }));
  await waitFor(() =>
    expect(executionsApi.getExecutions).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 }),
    ),
  );
});

it("indica polling rápido quando existe execução ativa", async () => {
  vi.mocked(executionsApi.getExecutions).mockResolvedValue({
    items: [{ ...completedExecution, status: "processing", terminal: false }],
    page: 1,
    page_size: 25,
    total: 1,
    pages: 1,
  });
  wrapper("/fila", <Route path="/fila" element={<ExecutionsPage />} />);

  expect(await screen.findByText("Atualizando a cada 2s")).toBeInTheDocument();
  expect(screen.getAllByText("Em execução")).toHaveLength(2);
});

it("expõe decisões, trace, notificação e payload no detalhe", async () => {
  const user = userEvent.setup();
  wrapper(
    `/fila/${completedExecution.id}`,
    <Route path="/fila/:executionId" element={<ExecutionDetailPage />} />,
  );

  expect(await screen.findByText("Linha do tempo")).toBeInTheDocument();
  expect(screen.getByText("worker-local")).toBeInTheDocument();
  expect(screen.getByText("Decisões e traces")).toBeInTheDocument();
  await user.click(screen.getByText("Envio autorizado"));
  expect(screen.getAllByText("DueTodayPolicy")).toHaveLength(2);
  expect(screen.getByText("Políticas avaliadas")).toBeInTheDocument();
  expect(screen.getByText(/UpcomingReminderPolicy/)).toBeInTheDocument();
  expect(screen.getByText(/Tentativa de notificação: simulated/)).toBeInTheDocument();
  await user.click(screen.getByText("Payload original"));
  expect(screen.getByText(/charge_id/)).toBeInTheDocument();
});
