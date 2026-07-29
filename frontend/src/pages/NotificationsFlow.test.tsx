import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as chargesApi from "../api/charges";
import * as customersApi from "../api/customers";
import * as notificationsApi from "../api/notifications";
import * as dashboardApi from "../api/dashboard";
import type { Charge, Customer, NotificationAttempt } from "../api/types";
import { NotificationDetailPage } from "./NotificationDetailPage";
import { NotificationsPage } from "./NotificationsPage";

vi.mock("../api/notifications", () => ({
  getNotifications: vi.fn(),
  getNotification: vi.fn(),
  getNotificationRecovery: vi.fn(),
  getNotificationAttempts: vi.fn(),
  retryNotification: vi.fn(),
  retryNotificationWithTemplate: vi.fn(),
}));
vi.mock("../api/dashboard", () => ({
  getDashboardSummary: vi.fn(),
  getJob: vi.fn(),
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
  submission_status: "simulated",
  provider_message_id: "wamid.fake.1",
  submission_error_code: null,
  submission_error_title: null,
  submission_error_details: null,
  submission_error_info: null,
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
  delivery_status: "pending",
  delivery_error_info: null,
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
  vi.mocked(notificationsApi.getNotificationRecovery).mockResolvedValue({
    attempt_id: attempt.id,
    eligible: false,
    action: "block",
    reason: "delivery_is_pending",
    policy_name: "BlockActiveOrSuccessfulDeliveryPolicy",
    trace: attempt.trace!,
  });
  vi.mocked(notificationsApi.getNotificationAttempts).mockResolvedValue([
    attempt,
  ]);
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

  expect(await screen.findByText(/Processamento no simulador/)).toBeInTheDocument();
  expect(screen.getByText(/Entrega simulada.*Aguardando entrega/)).toBeInTheDocument();
  expect(screen.getByText("Olá! Sua cobrança vence hoje.")).toBeInTheDocument();
  expect(await screen.findByText("Mensalidade de julho")).toBeInTheDocument();
  expect(await screen.findByText("Padaria Pão Dourado")).toBeInTheDocument();
  expect(screen.getByText("Execução job-1")).toBeInTheDocument();
  expect(screen.getByText("DueTodayPolicy")).toBeInTheDocument();
  expect(screen.getByText("Simulador local")).toBeInTheDocument();
  expect(screen.getByText("Simulado")).toBeInTheDocument();
  await user.click(screen.getByText("Dados técnicos sanitizados"));
  expect(screen.getByText(/simulated/)).toBeInTheDocument();
});

it("enfileira retentativa elegível e preserva o histórico", async () => {
  const user = userEvent.setup();
  const retried = {
    ...attempt,
    id: "notification-2",
    attempt_number: 2,
    root_attempt_id: attempt.id,
    retry_of_attempt_id: attempt.id,
    delivery_status: "pending" as const,
  };
  vi.mocked(notificationsApi.getNotificationRecovery).mockResolvedValue({
    attempt_id: attempt.id,
    eligible: true,
    action: "retry",
    reason: "confirmed_retryable_failure",
    policy_name: "AllowRetryPolicy",
    trace: attempt.trace!,
  });
  vi.mocked(notificationsApi.retryNotification).mockResolvedValue({
    job_id: "retry-job-1",
    status: "queued",
    created: true,
  });
  vi.mocked(dashboardApi.getJob).mockResolvedValue({
    id: "retry-job-1",
    type: "retry_notification",
    status: "completed",
    origin: "manual",
    charge_id: null,
    terminal: true,
    duration_ms: 10,
    payload: {},
    result: {
      evaluated: 0,
      eligible: 1,
      skipped: 0,
      simulated: 1,
      deduplicated: 0,
      notification_failed: 0,
      retried: true,
      cancelled: false,
      source_attempt_id: attempt.id,
      attempt_id: retried.id,
    },
    scheduled_for: "2026-07-29T12:01:00Z",
    attempts: 1,
    max_attempts: 3,
    started_at: "2026-07-29T12:01:00Z",
    finished_at: "2026-07-29T12:01:00Z",
    error: null,
    retain_deduplication_key: false,
    created_at: "2026-07-29T12:01:00Z",
    updated_at: "2026-07-29T12:01:00Z",
  });
  vi.mocked(notificationsApi.getNotificationAttempts)
    .mockResolvedValueOnce([attempt])
    .mockResolvedValue([attempt, retried]);

  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Tentar novamente" }),
  );

  await waitFor(() =>
    expect(notificationsApi.retryNotification).toHaveBeenCalledWith(
      attempt.id,
    ),
  );
  expect(
    await screen.findByText("Nova tentativa criada"),
  ).toBeInTheDocument();
  expect(
    await screen.findByText("Tentativa 2"),
  ).toBeInTheDocument();
});

it("oferece reenvio com template para falha fora da janela", async () => {
  const user = userEvent.setup();
  vi.mocked(notificationsApi.getNotificationRecovery).mockResolvedValue({
    attempt_id: attempt.id,
    eligible: false,
    template_eligible: true,
    action: "template",
    reason: "error_requires_template",
    policy_name: "RequireTemplatePolicy",
    trace: attempt.trace!,
  });
  vi.mocked(
    notificationsApi.retryNotificationWithTemplate,
  ).mockResolvedValue({
    job_id: "template-job-1",
    status: "queued",
    created: true,
  });
  vi.mocked(dashboardApi.getJob).mockResolvedValue({
    id: "template-job-1",
    type: "retry_notification",
    status: "completed",
    origin: "manual",
    charge_id: charge.id,
    terminal: true,
    duration_ms: 10,
    payload: { send_mode: "template" },
    result: {
      evaluated: 0,
      eligible: 1,
      skipped: 0,
      simulated: 1,
      deduplicated: 0,
      notification_failed: 0,
      retried: true,
      cancelled: false,
      source_attempt_id: attempt.id,
    },
    scheduled_for: "2026-07-29T12:01:00Z",
    attempts: 1,
    max_attempts: 3,
    started_at: "2026-07-29T12:01:00Z",
    finished_at: "2026-07-29T12:01:00Z",
    error: null,
    retain_deduplication_key: false,
    created_at: "2026-07-29T12:01:00Z",
    updated_at: "2026-07-29T12:01:00Z",
  });

  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  await user.click(
    await screen.findByRole("button", {
      name: "Reenviar com template",
    }),
  );
  await waitFor(() =>
    expect(
      notificationsApi.retryNotificationWithTemplate,
    ).toHaveBeenCalledWith(attempt.id),
  );
});

it("explica o aceite e o retorno sanitizado da Meta", async () => {
  vi.mocked(notificationsApi.getNotification).mockResolvedValue({
    ...attempt,
    provider: "meta",
    submission_status: "succeeded",
    delivery_status: "pending",
    provider_message_id: "wamid.meta-test",
    provider_response: {
      request: { to: "55*******0000", type: "text" },
      response: {
        messages: [{ id: "wamid.meta-test" }],
        http_status: 200,
        correlation_id: "notification-1",
      },
    },
  });
  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  expect(
    await screen.findByText("WhatsApp Cloud API da Meta"),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "A API da Meta aceitou a mensagem e devolveu um identificador.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Real")).toBeInTheDocument();
  expect(screen.getByText("200")).toBeInTheDocument();
  expect(screen.getAllByText("wamid.meta-test").length).toBeGreaterThan(0);
});

it("diferencia visualmente uma falha", async () => {
  vi.mocked(notificationsApi.getNotification).mockResolvedValue({
    ...attempt,
    submission_status: "failed",
    delivery_status: "not_started",
    submission_error_details: "Falha controlada no provider",
    submission_error_info: {
      code: null,
      title: "Falha informada pelo WhatsApp",
      message: "O WhatsApp não conseguiu processar ou entregar esta mensagem.",
      action: "Confira os detalhes técnicos e a configuração antes de tentar novamente.",
      action_type: "review",
      known: false,
      technical_title: null,
      technical_details: "Falha controlada no provider",
    },
    provider_response: null,
  });
  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  expect(
    await screen.findByText(/Processamento no simulador.*Falhou/),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText("Falha controlada no provider"),
  ).toHaveLength(2);
});

it("diferencia aceite da requisição e falha posterior na entrega", async () => {
  vi.mocked(notificationsApi.getNotification).mockResolvedValue({
    ...attempt,
    provider: "meta",
    submission_status: "succeeded",
    provider_message_id: "wamid.meta-failed",
    delivery_status: "failed",
    delivery_event_at: "2026-07-29T12:02:00Z",
    delivery_updated_at: "2026-07-29T12:02:01Z",
    delivery_error_code: 131047,
    delivery_error_title: "Re-engagement message",
    delivery_error_details: "A janela de 24 horas foi encerrada.",
    delivery_error_info: {
      code: 131047,
      title: "Conversa fora da janela de atendimento",
      message: "A mensagem não foi entregue porque passaram mais de 24 horas desde a última interação do cliente.",
      action: "Reenvie usando um template aprovado pela Meta.",
      action_type: "template",
      known: true,
      technical_title: "Re-engagement message",
      technical_details: "A janela de 24 horas foi encerrada.",
    },
    delivery_response: {
      status: "failed",
      recipient_id: "55*******0000",
    },
  });
  wrapper(
    "/notificacoes/notification-1",
    <Route path="/notificacoes/:notificationId" element={<NotificationDetailPage />} />,
  );

  expect(
    await screen.findByText("Conversa fora da janela de atendimento"),
  ).toBeInTheDocument();
  expect(screen.getAllByText("Falha na entrega").length).toBeGreaterThan(0);
  expect(screen.getByText("Re-engagement message")).toBeInTheDocument();
  expect(screen.getByText("Código Meta 131047")).toBeInTheDocument();
  expect(
    screen.getByText(
      "A Meta aceitou a requisição inicial, mas confirmou que a mensagem não foi entregue.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Evento de entrega sanitizado")).toBeInTheDocument();
});
