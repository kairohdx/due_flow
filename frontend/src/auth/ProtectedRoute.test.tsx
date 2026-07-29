import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import {
  markAuthInitialized,
  setAuthSession,
} from "./authStore";
import { ProtectedRoute } from "./ProtectedRoute";

function renderRoute() {
  return render(
    <MemoryRouter initialEntries={["/privado"]}>
      <Routes>
        <Route path="/login" element={<div>Tela de login</div>} />
        <Route
          path="/privado"
          element={
            <ProtectedRoute>
              <div>Conteúdo privado</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

it("redireciona usuário sem sessão para o login", () => {
  markAuthInitialized();
  renderRoute();
  expect(screen.getByText("Tela de login")).toBeInTheDocument();
});

it("renderiza rota privada quando existe access token", () => {
  setAuthSession("access-token");
  markAuthInitialized();
  renderRoute();
  expect(screen.getByText("Conteúdo privado")).toBeInTheDocument();
});
