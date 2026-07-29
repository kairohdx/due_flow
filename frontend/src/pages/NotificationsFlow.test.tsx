import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as chargesApi from "../api/charges";
import * as customersApi from "../api/customers";
import * as notificationsApi from "../api/notifications";
import type { Charge, Customer, NotificationAttempt } from "../api/types";
import { NotificationDetailPage } from "./NotificationDetailPage";
import { NotificationsPage } from "./NotificationsPage";

vi.mock("../api/notifications", () => ({
  getNotifications: vi.fn(),
  getNotification: vi.fn(),
}));
vi.mock("../api/charges", () => ({
  getCharge: vi.fn(),
}));
vi.mock("../api/customers", () => ({
  getCustomer: vi.fn(),
}));

const customer: Customer = {
  id: "customer-1",
  name: "Padaria Pão Dourado",
  phone: "+5511999990000",
  active: true,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-29T12:00:00Z",
};

const charge: Charge = {
  id: "charge-1",
  customer_id: customer.id,
  description: "Mensalidade de julho",
  amount: "150.00",
  due_date: "2026-07-29",
  status: "pending",
  reminder_days_before: 3,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-29T12:00:00Z",
};

const attempt: NotificationAttempt = {
  id: "notification-1",
  charge_id: charge.id,
  processing_job_id: "job-1",
  notification_type: "due_today",
  provider: "fake",
  destination: "+5511999990000",
  message: "Olá! Sua cobrança vence hoje.",
  status: "simulated",
  provider_message_id: "wamid.fake.1",
  error: null,
  idempotency_key: "charge-1:2026-07-29:due_today",
  policy_name: "DueTodayPolicy",
  decision_reason: "charge_is_due_today",
  trace: {
    trace_id: "trace-1",
    execution_id: "execution-1",
    pipeline: "charge_notification",
    strategy: "first_match",
    status: "completed",
    duration_ms: 1.5,
    selected_policy: "DueTodayPolicy",
    evaluated: [],
    not_evaluated: [],
  },
  provider_response: {
    request: { to: "5511999990000", type: "text" },
    response: { status: "simulated" },
  },
  processed_at: "2026-07-29T12:00:00Z",
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
  vi.mocked(notificationsApi.getNotifications).mockResolvedValue({
    items: [attempt],
    page: 1,
    page_size: 25,
    total: 26,
    pages: 2,
  });
  vi.mocked(notificationsApi.getNotification).mockResolvedValue(attempt);
  vi.mocked(chargesApi.getCharge).mockResolvedValue(charge);
  vi.mocked(customersApi.getCustomer).mockResolvedValue(customer);
});

it("lista notificações com filtros e paginação na URL", async () => {
  const user = userEvent.setup();
  wrapper(
    "/notificacoes",
    <Route path="/notificacoes" element={<NotificationsPage />} />,
  );

  expect(await screen.findByText("Vencimento hoje")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Filtrar resultado"), "simulated");
  await user.selectOptions(screen.getByLabelText("Filtrar canal"), "fake");
  await waitFor(() =>
    expect(notificationsApi.getNotifications).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "simulated", provider: "fake", page: 1 }),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Próxima página" }));
  await waitFor(() =>
    expect(notificationsApi.getNotifications).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 }),
    ),
  );
});

it("mostra conteúdo, rastreabilidade e vínculos no detalhe", async () => {
  const user = userEvent.setup();
  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  expect(await screen.findByText("Envio simulado com sucesso")).toBeInTheDocument();
  expect(screen.getByText("Olá! Sua cobrança vence hoje.")).toBeInTheDocument();
  expect(await screen.findByText("Mensalidade de julho")).toBeInTheDocument();
  expect(await screen.findByText("Padaria Pão Dourado")).toBeInTheDocument();
  expect(screen.getByText("Execução job-1")).toBeInTheDocument();
  expect(screen.getByText("DueTodayPolicy")).toBeInTheDocument();
  await user.click(screen.getByText("Resposta do provider"));
  expect(screen.getByText(/simulated/)).toBeInTheDocument();
});

it("diferencia visualmente uma falha", async () => {
  vi.mocked(notificationsApi.getNotification).mockResolvedValue({
    ...attempt,
    status: "failed",
    error: "Falha controlada no provider",
    provider_response: null,
  });
  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  expect(await screen.findByText("Falha no envio")).toBeInTheDocument();
  expect(screen.getByText("Falha controlada no provider")).toBeInTheDocument();
});
