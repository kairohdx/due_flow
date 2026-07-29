import type { ReactNode } from "react";
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
  formatDuration,
  formatInterval,
  formatTime,
} from "../lib/format";

const statusMeta: Record<
  JobStatus,
  { label: string; tone: BadgeTone; icon: IconName }
> = {
  queued: { label: "Na fila", tone: "warning", icon: "clock" },
  processing: { label: "Processando", tone: "info", icon: "activity" },
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
              : "Ative para que o worker crie jobs automaticamente no intervalo configurado."}
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

function RecentActivity({
  jobs,
  loading,
  error,
}: {
  jobs: Job[] | undefined;
  loading: boolean;
  error: unknown;
}) {
  return (
    <section className="surface-card activity-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Últimos eventos</span>
          <h2>Atividade recente</h2>
        </div>
        <span className="section-caption">Atualização automática</span>
      </div>
      {error && !jobs ? <ErrorState error={error} /> : null}
      {loading && !jobs ? <Skeleton lines={5} /> : null}
      {jobs?.length === 0 ? (
        <div className="activity-empty">
          <Icon name="activity" />
          <div><strong>Nenhum job por enquanto</strong><span>Processe agora ou ative a automação.</span></div>
        </div>
      ) : null}
      {jobs?.length ? (
        <div className="activity-list">
          {jobs.map((job) => {
            const meta = statusMeta[job.status];
            return (
              <article className="activity-row" key={job.id}>
                <span className={`activity-icon activity-${job.status}`}>
                  <Icon name={meta.icon} />
                </span>
                <div className="activity-copy">
                  <strong>
                    {job.origin === "automatic" ? "Processamento automático" : "Processamento manual"}
                  </strong>
                  <span>
                    {job.result
                      ? `${job.result.evaluated} avaliadas · ${job.result.simulated} simuladas`
                      : `Tentativa ${job.attempts} de ${job.max_attempts}`}
                  </span>
                </div>
                <div className="activity-meta">
                  <StatusBadge tone={meta.tone}>{meta.label}</StatusBadge>
                  <small>{formatTime(job.created_at)} · {formatDuration(job.duration_ms)}</small>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
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
            ? "Não foi possível iniciar o processamento"
            : job?.terminal
              ? job.status === "completed"
                ? "Processamento concluído"
                : "Processamento encerrado com falha"
              : "Processamento enviado para a fila"}
        </strong>
        <span>
          {error
            ? userFacingError(error)
            : job?.result
              ? `${job.result.evaluated} cobranças avaliadas e ${job.result.simulated} mensagens simuladas.`
              : "Acompanhando o status automaticamente, sem recarregar a página."}
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
        Processar agora
      </Button>
    </>
  );

  return (
    <div className="page-stack dashboard-page">
      <PageHeader
        eyebrow="Operação em tempo real"
        title={`Olá, ${firstName}.`}
        description="Acompanhe a automação e o trabalho da fila sem precisar atualizar a página."
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
            <MetricCard label="Cobranças pendentes" value={summary.charges_pending} hint="Aguardando resolução" icon="credit-card" tone="amber" />
            <MetricCard label="Cobranças avaliadas" value={summary.charges_evaluated_last_24h} hint="Últimas 24 horas" icon="activity" tone="blue" active={summary.jobs_processing > 0} />
            <MetricCard label="Mensagens processadas" value={summary.notifications_processed_last_24h} hint="Enviadas ou simuladas em 24h" icon="check" tone="teal" />
            <MetricCard label="Retries" value={summary.job_retries_last_24h} hint="Últimas 24 horas" icon="refresh" tone="amber" />
            <MetricCard label="Falhas de notificação" value={summary.notification_failures_last_24h} hint="Últimas 24 horas" icon="x" tone="red" />
          </section>
        </>
      )}

      <section className="dashboard-lower-grid">
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
        <RecentActivity
          jobs={dashboard.recentJobs.data?.items}
          loading={dashboard.recentJobs.isLoading}
          error={dashboard.recentJobs.error}
        />
      </section>
    </div>
  );
}
