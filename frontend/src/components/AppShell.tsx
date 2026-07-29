import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { logout } from "../auth/authService";
import { clearAuthState, useAuthState } from "../auth/authStore";
import { getAutomation } from "../api/dashboard";
import { Button } from "./ui/Button";
import { Icon, type IconName } from "./ui/Icon";

const navItems: { to: string; label: string; icon: IconName }[] = [
  { to: "/", label: "Visão geral", icon: "dashboard" },
  { to: "/clientes", label: "Clientes", icon: "users" },
  { to: "/cobrancas", label: "Cobranças", icon: "credit-card" },
  { to: "/fila", label: "Execuções da automação", icon: "activity" },
  { to: "/notificacoes", label: "Histórico de mensagens", icon: "message" },
];

const routeTitles: Record<string, string> = {
  "/": "Visão geral",
  "/clientes": "Clientes",
  "/cobrancas": "Cobranças",
  "/fila": "Execuções da automação",
  "/notificacoes": "Histórico de mensagens",
  "/configuracoes": "Configurações",
};

export function AppShell() {
  const auth = useAuthState();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const automation = useQuery({
    queryKey: ["automation"],
    queryFn: getAutomation,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  async function onLogout() {
    try {
      await logout();
    } finally {
      clearAuthState();
      queryClient.clear();
      navigate("/login", { replace: true });
    }
  }

  const initials = auth.user?.name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  const currentTitle =
    routeTitles[location.pathname] ??
    (location.pathname.startsWith("/clientes")
      ? "Clientes"
      : location.pathname.startsWith("/cobrancas")
        ? "Cobranças"
        : location.pathname.startsWith("/fila")
          ? "Execuções da automação"
          : location.pathname.startsWith("/notificacoes")
            ? "Histórico de mensagens"
        : "DueFlow");

  return (
    <div className={`app-shell ${menuOpen ? "menu-open" : ""}`}>
      <a className="skip-link" href="#conteudo-principal">
        Ir para o conteúdo principal
      </a>
      <button
        className="sidebar-backdrop"
        aria-label="Fechar menu"
        onClick={() => setMenuOpen(false)}
      />
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">D</span>
          <div><strong>DueFlow</strong><small>Central financeira</small></div>
          <button
            className="icon-button sidebar-close"
            onClick={() => setMenuOpen(false)}
            aria-label="Fechar menu"
          >
            <Icon name="x" />
          </button>
        </div>
        <div className="sidebar-label">Operação</div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              end={item.to === "/"}
              key={item.to}
              onClick={() => setMenuOpen(false)}
              to={item.to}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <NavLink
            aria-label={`Automação: ${
              automation.isLoading
                ? "consultando estado"
                : automation.isError
                  ? "estado indisponível"
                  : automation.data?.enabled
                    ? "ativa"
                    : "pausada"
            }`}
            className="automation-mini"
            to="/configuracoes"
          >
            <span
              className={`automation-indicator ${automation.data?.enabled ? "enabled" : ""}`}
            />
            <div>
              <strong>Automação</strong>
              <small aria-live="polite">
                {automation.isLoading
                  ? "Consultando estado..."
                  : automation.isError
                    ? "Estado indisponível"
                  : automation.data?.enabled
                    ? "Ativa"
                    : "Pausada"}
              </small>
            </div>
          </NavLink>
          <NavLink className="nav-link" to="/configuracoes">
            <Icon name="settings" />
            <span>Configurações</span>
          </NavLink>
        </div>
      </aside>

      <div className="shell-main">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className="icon-button mobile-menu"
              onClick={() => setMenuOpen(true)}
              aria-label="Abrir menu"
            >
              <Icon name="menu" />
            </button>
            <div>
              <span className="topbar-context">Painel</span>
              <strong>{currentTitle}</strong>
            </div>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button notification-button"
              aria-label="Abrir histórico de mensagens"
              onClick={() => navigate("/notificacoes")}
            >
              <Icon name="bell" />
            </button>
            <div className="user-menu-wrap">
              <button
                className="user-trigger"
                onClick={() => setUserMenuOpen((open) => !open)}
                aria-label="Abrir menu da conta"
                aria-expanded={userMenuOpen}
              >
                <span className="avatar">{initials || "DF"}</span>
                <span className="user-copy">
                  <strong>{auth.user?.name}</strong>
                  <small>{auth.user?.email}</small>
                </span>
                <Icon name="chevron-down" />
              </button>
              {userMenuOpen ? (
                <div className="user-popover">
                  <div>
                    <strong>{auth.user?.name}</strong>
                    <small>{auth.user?.email}</small>
                  </div>
                  <Button
                    variant="ghost"
                    icon={<Icon name="logout" />}
                    onClick={() => void onLogout()}
                  >
                    Sair da conta
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </header>
        <main className="page-content" id="conteudo-principal" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
