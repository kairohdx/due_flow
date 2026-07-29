import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { getMe, login } from "../auth/authService";
import { setAuthSession, useAuthState } from "../auth/authStore";
import { userFacingError } from "../api/errors";
import { Button } from "../components/ui/Button";
import { Icon } from "../components/ui/Icon";
import { AppLoading } from "../components/feedback/AppLoading";

export function LoginPage() {
  const auth = useAuthState();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!auth.initialized) return <AppLoading />;
  if (auth.accessToken) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login({ email, password });
      const user = await getMe(token.access_token);
      setAuthSession(token.access_token, user);
      const state = location.state as { from?: string } | null;
      navigate(state?.from ?? "/", { replace: true });
    } catch (caught) {
      setError(userFacingError(caught));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-showcase" aria-label="Apresentação do DueFlow">
        <div className="auth-showcase-content">
          <div className="auth-brand">
            <span className="brand-mark">D</span>
            <span>DueFlow</span>
          </div>
          <div className="auth-copy">
            <span className="auth-pill">
              <Icon name="sparkles" />
              Cobranças que trabalham por você
            </span>
            <h1>Automação clara.<br />Controle em cada decisão.</h1>
            <p>
              Organize cobranças, acompanhe a fila e entenda exatamente por que
              cada lembrete foi enviado.
            </p>
          </div>
          <div className="auth-preview" aria-hidden="true">
            <div className="preview-glow" />
            <div className="preview-card preview-card-main">
              <span>Processamento automático</span>
              <strong>Operando normalmente</strong>
              <div className="preview-progress"><i /></div>
            </div>
            <div className="preview-card preview-card-float">
              <span className="preview-dot" />
              <div><strong>12 processados</strong><small>nas últimas 24 horas</small></div>
            </div>
          </div>
        </div>
      </section>

      <section className="auth-form-section">
        <div className="auth-form-wrap">
          <div className="auth-mobile-brand">
            <span className="brand-mark">D</span>
            <span>DueFlow</span>
          </div>
          <div className="auth-heading">
            <span className="eyebrow">Bem-vindo de volta</span>
            <h2>Acesse seu painel</h2>
            <p>Entre com os dados do administrador.</p>
          </div>

          <form className="auth-form" onSubmit={onSubmit}>
            <label>
              <span>E-mail</span>
              <input
                autoComplete="email"
                inputMode="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="voce@empresa.com"
                required
                type="email"
                value={email}
              />
            </label>
            <label>
              <span>Senha</span>
              <input
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Digite sua senha"
                required
                type="password"
                value={password}
              />
            </label>
            {error ? <div className="auth-error" role="alert">{error}</div> : null}
            <Button
              className="auth-submit"
              loading={loading}
              type="submit"
              icon={<Icon name="arrow-right" />}
            >
              Entrar no DueFlow
            </Button>
          </form>
          <p className="auth-security">
            Sua sessão é protegida e renovada com segurança.
          </p>
        </div>
      </section>
    </main>
  );
}
