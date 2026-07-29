import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { DashboardSummary } from "../api/dashboard";
import { useAuthState } from "../auth/authStore";
import type { Job, JobStatus } from "../api/types";
import { userFacingError } from "../api/errors";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { Button } from "../components/ui/Button";
import { Icon, type IconName } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge, type BadgeTone } from "../components/ui/StatusBadge";
import { useDashboard } from "../hooks/useDashboard";
import {
  formatDateTime,
  formatInterval,
  formatTime,
} from "../lib/format";

const statusMeta: Record<
  JobStatus,
  { label: string; tone: BadgeTone; icon: IconName }
> = {
  queued: { label: "Aguardando", tone: "warning", icon: "clock" },
  processing: { label: "Verificando", tone: "info", icon: "activity" },
  completed: { label: "Concluído", tone: "success", icon: "check" },
  failed: { label: "Falhou", tone: "danger", icon: "x" },
};

function MetricCard({
  label,
  value,
  hint,
  icon,
  tone = "blue",
  active = false,
}: {
  label: string;
  value: number;
  hint: string;
  icon: IconName;
  tone?: "blue" | "teal" | "amber" | "red" | "slate";
  active?: boolean;
}) {
  return (
    <article className={`metric-card metric-${tone} ${active ? "metric-active" : ""}`}>
      <div className="metric-top">
        <span className="metric-icon"><Icon name={icon} /></span>
        {active ? <span className="live-label"><i />Ao vivo</span> : null}
      </div>
      <strong>{value.toLocaleString("pt-BR")}</strong>
      <span>{label}</span>
      <small>{hint}</small>
    </article>
  );
}

function AutomationCard({
  state,
  loading,
  error,
  onEnable,
  onDisable,
}: {
  state: ReturnType<typeof useDashboard>["automation"]["data"];
  loading: boolean;
  error: unknown;
  onEnable: () => void;
  onDisable: () => void;
}) {
  if (error && !state) return <ErrorState error={error} />;
  return (
    <section className="surface-card automation-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Execução recorrente</span>
          <h2>Automação</h2>
        </div>
        <StatusBadge tone={state?.enabled ? "success" : "neutral"}>
          <span className={`status-pulse ${state?.enabled ? "enabled" : ""}`} />
          {state?.enabled ? "Ativa" : "Pausada"}
        </StatusBadge>
      </div>
      {!state ? (
        <Skeleton lines={4} />
      ) : (
        <>
          <p className="automation-description">
            {state.enabled
              ? `O DueFlow verifica novas cobranças a cada ${formatInterval(state.interval_seconds)}.`
              : "Ative para verificar cobranças e enviar lembretes automaticamente."}
          </p>
          <dl className="automation-details">
            <div><dt>Intervalo</dt><dd>{formatInterval(state.interval_seconds)}</dd></div>
            <div><dt>Último disparo</dt><dd>{formatDateTime(state.last_enqueued_at)}</dd></div>
            <div><dt>Próximo disparo</dt><dd>{state.enabled ? formatDateTime(state.next_run_at) : "Pausado"}</dd></div>
          </dl>
          {error ? (
            <div className="inline-error" role="alert">
              {userFacingError(error)}
            </div>
          ) : null}
          <Button
            variant={state.enabled ? "secondary" : "primary"}
            loading={loading}
            icon={<Icon name={state.enabled ? "pause" : "play"} />}
            onClick={state.enabled ? onDisable : onEnable}
          >
            {state.enabled ? "Pausar automação" : "Ativar automação"}
          </Button>
        </>
      )}
    </section>
  );
}

function AttentionCard({ summary }: { summary: DashboardSummary }) {
  const attentionTotal =
    summary.charges_overdue +
    summary.charges_due_today +
    summary.submissions_failed_last_24h +
    summary.submissions_unknown_last_24h +
    summary.deliveries_failed_last_24h;
  const items = [
    {
      label: "Cobranças vencidas",
      value: summary.charges_overdue,
      hint: "Aguardando resolução",
      icon: "bell" as const,
      tone: "danger",
      to: "/cobrancas?status=pending",
    },
    {
      label: "Vencem hoje",
      value: summary.charges_due_today,
      hint: "Prazo termina hoje",
      icon: "calendar" as const,
      tone: "warning",
      to: "/cobrancas?status=pending",
    },
    {
      label: "Falhas ao enviar para a Meta",
      value: summary.submissions_failed_last_24h,
      hint: "Ocorridas nas últimas 24h",
      icon: "x" as const,
      tone: "danger",
      to: "/notificacoes",
    },
    {
      label: "Falhas na entrega pelo WhatsApp",
      value: summary.deliveries_failed_last_24h,
      hint: "Informadas por webhook nas últimas 24h",
      icon: "x" as const,
      tone: "danger",
      to: "/notificacoes",
    },
    {
      label: "Envios com resultado incerto",
      value: summary.submissions_unknown_last_24h,
      hint: "Precisam de revisão antes de reenviar",
      icon: "clock" as const,
      tone: "warning",
      to: "/notificacoes?status=unknown",
    },
  ];

  return (
    <section className="surface-card attention-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Prioridades</span>
          <h2>Atenção necessária</h2>
        </div>
        <StatusBadge tone={attentionTotal > 0 ? "warning" : "success"}>
          {attentionTotal > 0 ? `${attentionTotal} pendência(s)` : "Tudo em ordem"}
        </StatusBadge>
      </div>
      <div className="attention-list">
        {items.map((item) => (
          <Link className="attention-row" key={item.label} to={item.to}>
            <span className={`attention-icon attention-${item.tone}`}>
              <Icon name={item.icon} />
            </span>
            <span>
              <strong>{item.label}</strong>
              <small>{item.hint}</small>
            </span>
            <b>{item.value.toLocaleString("pt-BR")}</b>
            <Icon name="arrow-right" />
          </Link>
        ))}
      </div>
    </section>
  );
}

function ProcessBanner({
  job,
  pending,
  error,
}: {
  job: Job | undefined;
  pending: boolean;
  error: unknown;
}) {
  if (!job && !pending && !error) return null;
  const meta = job ? statusMeta[job.status] : statusMeta.queued;
  return (
    <div className={`process-banner process-${job?.status ?? "queued"}`} role="status">
      <span className="process-banner-icon"><Icon name={meta.icon} /></span>
      <div>
        <strong>
          {error
            ? "Não foi possível iniciar a verificação"
            : job?.terminal
              ? job.status === "completed"
                ? "Verificação concluída"
                : "Verificação encerrada com falha"
              : "Verificação adicionada à fila"}
        </strong>
        <span>
          {error
            ? userFacingError(error)
            : job?.result
              ? job.result.simulated > 0
                ? `${job.result.simulated} mensagem(ns) enviada(s) nesta verificação.`
                : "Nenhuma mensagem precisou ser enviada nesta verificação."
              : "O resultado será atualizado automaticamente."}
        </span>
      </div>
      {!error ? <StatusBadge tone={meta.tone}>{meta.label}</StatusBadge> : null}
    </div>
  );
}

export function DashboardPage() {
  const auth = useAuthState();
  const dashboard = useDashboard();
  const summary = dashboard.summary.data;
  const automationMutationPending =
    dashboard.enable.isPending || dashboard.disable.isPending;
  const firstName = auth.user?.name.split(/\s+/)[0] ?? "Administrador";

  const headerAction: ReactNode = (
    <>
      <Button
        variant="secondary"
        icon={<Icon name="refresh" />}
        onClick={dashboard.refreshAll}
      >
        Atualizar
      </Button>
      <Button
        icon={<Icon name="play" />}
        loading={dashboard.processNow.isPending}
        onClick={() => dashboard.processNow.mutate()}
      >
        Verificar agora
      </Button>
    </>
  );

  return (
    <div className="page-stack dashboard-page">
      <PageHeader
        eyebrow="Resumo do negócio"
        title={`Olá, ${firstName}.`}
        description="Acompanhe cobranças, vencimentos e lembretes em uma visão simples."
        actions={headerAction}
      />

      <ProcessBanner
        pending={dashboard.processNow.isPending}
        error={dashboard.processNow.error ?? dashboard.trackedJob.error}
        job={dashboard.trackedJob.data}
      />

      {dashboard.summary.error && !summary ? (
        <ErrorState
          error={dashboard.summary.error}
          onRetry={() => void dashboard.summary.refetch()}
        />
      ) : null}

      {!summary ? (
        <section className="metrics-grid">
          {Array.from({ length: 6 }, (_, index) => (
            <div className="metric-card" key={index}><Skeleton lines={3} /></div>
          ))}
        </section>
      ) : (
        <>
          <div className="dashboard-update-line">
            <span><i />Dados atualizados às {formatTime(summary.generated_at)}</span>
            <span>Janela móvel de 24 horas</span>
          </div>
          <section className="metrics-grid">
            <MetricCard label="Clientes cadastrados" value={summary.customers_total} hint="Base total" icon="users" />
            <MetricCard label="Cobranças em aberto" value={summary.charges_pending} hint="Aguardando resolução" icon="credit-card" tone="amber" />
            <MetricCard label="Cobranças vencidas" value={summary.charges_overdue} hint="Precisam de atenção" icon="bell" tone="red" />
            <MetricCard label="Vencem hoje" value={summary.charges_due_today} hint="Prazo de hoje" icon="calendar" tone="amber" />
            <MetricCard label="Vencem em até 7 dias" value={summary.charges_due_next_7_days} hint="Próximos vencimentos" icon="clock" tone="blue" />
            <MetricCard label="Envios aceitos pela Meta" value={summary.submissions_succeeded_last_24h} hint="Últimas 24 horas" icon="check" tone="teal" />
          </section>
        </>
      )}

      <section className="dashboard-business-lower">
        <AutomationCard
          state={dashboard.automation.data}
          loading={automationMutationPending}
          error={
            dashboard.automation.error ??
            dashboard.enable.error ??
            dashboard.disable.error
          }
          onEnable={() => dashboard.enable.mutate()}
          onDisable={() => dashboard.disable.mutate()}
        />
        {summary ? <AttentionCard summary={summary} /> : <Skeleton lines={6} />}
      </section>
    </div>
  );
}
