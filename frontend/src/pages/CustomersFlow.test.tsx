import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as customersApi from "../api/customers";
import type { Customer } from "../api/types";
import { CustomerCreatePage } from "./CustomerCreatePage";
import { CustomerDetailPage } from "./CustomerDetailPage";
import { CustomersPage } from "./CustomersPage";

vi.mock("../api/customers", () => ({
  getCustomers: vi.fn(),
  getCustomer: vi.fn(),
  createCustomer: vi.fn(),
  updateCustomer: vi.fn(),
  getCustomerCharges: vi.fn(),
}));

const customer: Customer = {
  id: "customer-1",
  name: "Empresa Exemplo",
  phone: "+5511999990000",
  active: true,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-29T12:00:00Z",
};

function wrapper(initialEntry: string, routes: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
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
  vi.mocked(customersApi.getCustomers).mockResolvedValue({
    items: [customer],
    page: 1,
    page_size: 25,
    total: 26,
    pages: 2,
  });
  vi.mocked(customersApi.getCustomer).mockResolvedValue(customer);
  vi.mocked(customersApi.getCustomerCharges).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 25,
    total: 0,
    pages: 0,
  });
  vi.mocked(customersApi.createCustomer).mockResolvedValue(customer);
  vi.mocked(customersApi.updateCustomer).mockImplementation(
    async (_id, payload) => ({ ...customer, ...payload }),
  );
});

it("lista clientes e mantém busca e paginação nos parâmetros", async () => {
  const user = userEvent.setup();
  wrapper(
    "/clientes",
    <Route path="/clientes" element={<CustomersPage />} />,
  );

  expect(await screen.findByText("Empresa Exemplo")).toBeInTheDocument();
  await user.type(screen.getByLabelText("Buscar clientes"), "Empresa");
  await user.keyboard("{Enter}");

  await waitFor(() =>
    expect(customersApi.getCustomers).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Empresa", page: 1 }),
    ),
  );

  await user.click(screen.getByRole("button", { name: "Próxima página" }));
  await waitFor(() =>
    expect(customersApi.getCustomers).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Empresa", page: 2 }),
    ),
  );
});

it("cadastra cliente e navega para o detalhe", async () => {
  const user = userEvent.setup();
  wrapper(
    "/clientes/novo",
    <>
      <Route path="/clientes/novo" element={<CustomerCreatePage />} />
      <Route path="/clientes/:customerId" element={<div>Detalhe criado</div>} />
    </>,
  );

  await user.type(screen.getByLabelText("Nome do cliente"), "Empresa Exemplo");
  await user.type(screen.getByLabelText("WhatsApp"), "+55 11 99999-0000");
  await user.click(screen.getByRole("button", { name: "Cadastrar cliente" }));

  expect(customersApi.createCustomer).toHaveBeenCalledWith(
    {
      name: "Empresa Exemplo",
      phone: "+55 11 99999-0000",
      active: true,
    },
    expect.anything(),
  );
  expect(await screen.findByText("Detalhe criado")).toBeInTheDocument();
});

it("exibe cobranças relacionadas e permite editar o cliente", async () => {
  const user = userEvent.setup();
  wrapper(
    "/clientes/customer-1",
    <Route path="/clientes/:customerId" element={<CustomerDetailPage />} />,
  );

  expect(await screen.findByText("+55 (11) 99999-0000")).toBeInTheDocument();
  expect(screen.getByText("Nenhuma cobrança cadastrada")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Editar cliente" }));
  const name = screen.getByLabelText("Nome do cliente");
  await user.clear(name);
  await user.type(name, "Empresa Atualizada");
  await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

  await waitFor(() =>
    expect(customersApi.updateCustomer).toHaveBeenCalledWith(
      "customer-1",
      expect.objectContaining({ name: "Empresa Atualizada" }),
    ),
  );
  expect(
    await screen.findByRole("heading", { level: 1, name: "Empresa Atualizada" }),
  ).toBeInTheDocument();
});
