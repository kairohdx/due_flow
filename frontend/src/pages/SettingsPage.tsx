import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { userFacingError } from "../api/errors";
import type { AutomationState } from "../api/dashboard";
import { clearAuthState, useAuthState } from "../auth/authStore";
import { Skeleton } from "../components/feedback/Skeleton";
import { ErrorState } from "../components/feedback/ErrorState";
import { Button } from "../components/ui/Button";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useSettings } from "../hooks/useSettings";
import { formatDateTime, formatInterval } from "../lib/format";

function AutomationSettingsForm({
  state,
  settings,
}: {
  state: AutomationState;
  settings: ReturnType<typeof useSettings>;
}) {
  const [minutes, setMinutes] = useState(
    String(Math.max(1, state.interval_seconds / 60)),
  );
  const pending =
    settings.configure.isPending ||
    settings.enable.isPending ||
    settings.disable.isPending;
  const error =
    settings.configure.error ?? settings.enable.error ?? settings.disable.error;

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    settings.configure.mutate(Math.round(Number(minutes) * 60));
  }

  return (
    <div className="settings-automation-content">
      <div className="settings-status-line">
        <div>
          <strong>{state.enabled ? "Automação ativa" : "Automação pausada"}</strong>
          <small>
            {state.enabled
              ? `Verificações a cada ${formatInterval(state.interval_seconds)}.`
              : "Nenhuma verificação recorrente será iniciada."}
          </small>
        </div>
        <StatusBadge tone={state.enabled ? "success" : "neutral"}>
          {state.enabled ? "Ativa" : "Pausada"}
        </StatusBadge>
      </div>
      <form className="settings-inline-form" onSubmit={save}>
        <label className="form-field">
          <span>Intervalo entre verificações</span>
          <div className="input-suffix">
            <input
              aria-label="Intervalo em minutos"
              min="1"
              max="1440"
              onChange={(event) => setMinutes(event.target.value)}
              required
              step="1"
              type="number"
              value={minutes}
            />
            <span>minutos</span>
          </div>
          <small>O novo intervalo será usado nos próximos ciclos.</small>
        </label>
        <Button loading={settings.configure.isPending} type="submit" variant="secondary">
          Salvar intervalo
        </Button>
      </form>
      <dl className="settings-facts">
        <div><dt>Última verificação</dt><dd>{formatDateTime(state.last_enqueued_at)}</dd></div>
        <div><dt>Próxima verificação</dt><dd>{state.enabled ? formatDateTime(state.next_run_at) : "Pausada"}</dd></div>
      </dl>
      {error ? <div className="form-error" role="alert">{userFacingError(error)}</div> : null}
      {settings.configure.isSuccess && !error ? (
        <div className="feedback-banner feedback-success" role="status">
          Intervalo atualizado.
        </div>
      ) : null}
      <Button
        disabled={pending}
        icon={<Icon name={state.enabled ? "pause" : "play"} />}
        onClick={() =>
          state.enabled ? settings.disable.mutate() : settings.enable.mutate()
        }
      >
        {state.enabled ? "Pausar automação" : "Ativar automação"}
      </Button>
    </div>
  );
}

function PasswordForm({ settings }: { settings: ReturnType<typeof useSettings> }) {
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const mismatch = confirmation.length > 0 && newPassword !== confirmation;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== confirmation) return;
    settings.password.mutate(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => {
          clearAuthState();
          navigate("/login?password=changed", { replace: true });
        },
      },
    );
  }

  return (
    <form className="settings-password-form" onSubmit={submit}>
      <label className="form-field">
        <span>Senha atual</span>
        <input
          aria-label="Senha atual"
          autoComplete="current-password"
          onChange={(event) => setCurrentPassword(event.target.value)}
          required
          type="password"
          value={currentPassword}
        />
      </label>
      <label className="form-field">
        <span>Nova senha</span>
        <input
          aria-label="Nova senha"
          autoComplete="new-password"
          minLength={8}
          onChange={(event) => setNewPassword(event.target.value)}
          required
          type="password"
          value={newPassword}
        />
        <small>Use pelo menos 8 caracteres.</small>
      </label>
      <label className="form-field">
        <span>Confirmar nova senha</span>
        <input
          aria-label="Confirmar nova senha"
          autoComplete="new-password"
          onChange={(event) => setConfirmation(event.target.value)}
          required
          type="password"
          value={confirmation}
        />
        {mismatch ? <small className="field-error">As senhas não coincidem.</small> : null}
      </label>
      {settings.password.error ? (
        <div className="form-error settings-form-wide" role="alert">
          {userFacingError(settings.password.error)}
        </div>
      ) : null}
      <Button
        className="settings-form-wide"
        disabled={mismatch}
        loading={settings.password.isPending}
        type="submit"
        variant="secondary"
      >
        Alterar senha
      </Button>
    </form>
  );
}

export function SettingsPage() {
  const auth = useAuthState();
  const settings = useSettings();
  return (
    <div className="page-stack settings-page">
      <PageHeader
        eyebrow="Preferências e segurança"
        title="Configurações"
        description="Gerencie sua conta e o funcionamento recorrente da automação."
      />
      <section className="settings-grid">
        <article className="surface-card settings-card">
          <div className="settings-card-heading">
            <span><Icon name="users" /></span>
            <div><h2>Conta</h2><p>Dados usados para identificar sua sessão.</p></div>
          </div>
          <dl className="settings-facts">
            <div><dt>Nome</dt><dd>{auth.user?.name ?? "—"}</dd></div>
            <div><dt>E-mail</dt><dd>{auth.user?.email ?? "—"}</dd></div>
          </dl>
        </article>
        <article className="surface-card settings-card settings-automation-card">
          <div className="settings-card-heading">
            <span><Icon name="activity" /></span>
            <div><h2>Automação</h2><p>Defina quando as cobranças serão verificadas.</p></div>
          </div>
          {settings.automation.data ? (
            <AutomationSettingsForm
              key={settings.automation.data.updated_at}
              settings={settings}
              state={settings.automation.data}
            />
          ) : settings.automation.error ? (
            <ErrorState
              error={settings.automation.error}
              onRetry={() => void settings.automation.refetch()}
            />
          ) : (
            <Skeleton lines={6} />
          )}
        </article>
        <article className="surface-card settings-card settings-security-card">
          <div className="settings-card-heading">
            <span><Icon name="settings" /></span>
            <div><h2>Segurança</h2><p>Alterar a senha encerra todas as sessões abertas.</p></div>
          </div>
          <PasswordForm settings={settings} />
        </article>
      </section>
    </div>
  );
}
