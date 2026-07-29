import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as chargesApi from "../api/charges";
import * as customersApi from "../api/customers";
import type { Charge, Customer } from "../api/types";
import { ChargeCreatePage } from "./ChargeCreatePage";
import { ChargeDetailPage } from "./ChargeDetailPage";
import { ChargesPage } from "./ChargesPage";

vi.mock("../api/charges", () => ({
  getCharges: vi.fn(),
  getCharge: vi.fn(),
  createCharge: vi.fn(),
  updateCharge: vi.fn(),
  markChargePaid: vi.fn(),
  cancelCharge: vi.fn(),
  processCharge: vi.fn(),
}));

vi.mock("../api/customers", () => ({
  getCustomers: vi.fn(),
  getCustomer: vi.fn(),
  getCustomerCharges: vi.fn(),
  createCustomer: vi.fn(),
  updateCustomer: vi.fn(),
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
  due_date: "2026-07-31",
  status: "pending",
  reminder_days_before: 3,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-29T12:00:00Z",
};

function wrapper(initialEntry: string, routes: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
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
  vi.mocked(chargesApi.getCharges).mockResolvedValue({
    items: [charge],
    page: 1,
    page_size: 25,
    total: 26,
    pages: 2,
  });
  vi.mocked(chargesApi.getCharge).mockResolvedValue(charge);
  vi.mocked(chargesApi.createCharge).mockResolvedValue(charge);
  vi.mocked(chargesApi.updateCharge).mockImplementation(
    async (_id, payload) => ({ ...charge, ...payload }),
  );
  vi.mocked(chargesApi.markChargePaid).mockResolvedValue({ ...charge, status: "paid" });
  vi.mocked(chargesApi.cancelCharge).mockResolvedValue({ ...charge, status: "canceled" });
  vi.mocked(chargesApi.processCharge).mockResolvedValue({
    job_id: "job-12345678",
    status: "queued",
    created: true,
  });
  vi.mocked(customersApi.getCustomers).mockResolvedValue({
    items: [customer],
    page: 1,
    page_size: 25,
    total: 1,
    pages: 1,
  });
  vi.mocked(customersApi.getCustomer).mockResolvedValue(customer);
});

it("lista cobranças e aplica filtros persistidos na URL", async () => {
  const user = userEvent.setup();
  wrapper("/cobrancas", <Route path="/cobrancas" element={<ChargesPage />} />);

  expect(await screen.findByText("Mensalidade de julho")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Filtrar estado"), "pending");
  await user.type(screen.getByLabelText("Buscar cobranças"), "julho");
  await user.keyboard("{Enter}");

  await waitFor(() =>
    expect(chargesApi.getCharges).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "pending", search: "julho", page: 1 }),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Próxima página" }));
  await waitFor(() =>
    expect(chargesApi.getCharges).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 }),
    ),
  );
});

it("cadastra uma cobrança e navega para o detalhe", async () => {
  const user = userEvent.setup();
  wrapper(
    "/cobrancas/nova",
    <>
      <Route path="/cobrancas/nova" element={<ChargeCreatePage />} />
      <Route path="/cobrancas/:chargeId" element={<div>Detalhe criado</div>} />
    </>,
  );

  const customerSelect = await screen.findByLabelText("Cliente");
  await screen.findByRole("option", { name: customer.name });
  await user.selectOptions(customerSelect, customer.id);
  await user.type(screen.getByLabelText("Descrição"), "Mensalidade de julho");
  await user.type(screen.getByLabelText("Valor"), "15000");
  await user.type(screen.getByLabelText("Vencimento"), "31072026");
  await user.click(screen.getByRole("button", { name: "Cadastrar cobrança" }));

  expect(chargesApi.createCharge).toHaveBeenCalledWith(
    expect.objectContaining({
      customer_id: customer.id,
      description: "Mensalidade de julho",
      amount: "150.00",
      due_date: "2026-07-31",
      reminder_days_before: 3,
    }),
    expect.anything(),
  );
  expect(await screen.findByText("Detalhe criado")).toBeInTheDocument();
});

it("confirma a verificação assíncrona e o pagamento", async () => {
  const user = userEvent.setup();
  wrapper(
    "/cobrancas/charge-1",
    <Route path="/cobrancas/:chargeId" element={<ChargeDetailPage />} />,
  );

  expect(await screen.findByText("Padaria Pão Dourado")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Verificar agora" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Adicionar à fila" }));
  expect(await screen.findByText("Verificação adicionada à fila.")).toBeInTheDocument();
  expect(chargesApi.processCharge).toHaveBeenCalledWith("charge-1");

  await user.click(screen.getByRole("button", { name: "Marcar como paga" }));
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Marcar como paga",
    }),
  );
  expect(await screen.findByText("Cobrança marcada como paga.")).toBeInTheDocument();
  expect(chargesApi.markChargePaid).toHaveBeenCalledWith("charge-1");
});
