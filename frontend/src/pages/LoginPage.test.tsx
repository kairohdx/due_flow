import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as authService from "../auth/authService";
import {
  markAuthInitialized,
  resetAuthStateForTests,
} from "../auth/authStore";
import { LoginPage } from "./LoginPage";

vi.mock("../auth/authService", () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}));

function renderLogin(initialEntry: string | { pathname: string; state?: unknown } = "/login") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/cobrancas" element={<div>Lista de cobranças</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  resetAuthStateForTests();
  markAuthInitialized();
  vi.clearAllMocks();
});

it("autentica e retorna para a rota privada com seus filtros", async () => {
  vi.mocked(authService.login).mockResolvedValue({
    access_token: "access-token-for-test",
    token_type: "bearer",
    expires_in: 900,
  });
  vi.mocked(authService.getMe).mockResolvedValue({
    id: "user-1",
    email: "admin@example.com",
    name: "Administrador",
  });
  const user = userEvent.setup();
  renderLogin({
    pathname: "/login",
    state: { from: "/cobrancas?status=pending&page=2" },
  });

  await user.type(screen.getByLabelText("E-mail"), "admin@example.com");
  await user.type(
    screen.getByLabelText("Senha"),
    ["not", "a", "real", "password"].join("-"),
  );
  await user.click(screen.getByRole("button", { name: "Entrar no DueFlow" }));

  expect(await screen.findByText("Lista de cobranças")).toBeInTheDocument();
  expect(authService.login).toHaveBeenCalledOnce();
  expect(authService.getMe).toHaveBeenCalledWith("access-token-for-test");
});

it("mantém o formulário e apresenta credencial inválida", async () => {
  vi.mocked(authService.login).mockRejectedValue(new TypeError("Falha de rede"));
  const user = userEvent.setup();
  renderLogin();

  await user.type(screen.getByLabelText("E-mail"), "admin@example.com");
  await user.type(
    screen.getByLabelText("Senha"),
    ["not", "a", "real", "password"].join("-"),
  );
  await user.click(screen.getByRole("button", { name: "Entrar no DueFlow" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Não foi possível conectar à API.",
  );
  expect(screen.getByLabelText("E-mail")).toHaveValue("admin@example.com");
});
