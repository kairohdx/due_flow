import { Link, useParams } from "react-router-dom";
import type { Job, JobEvaluation } from "../api/types";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useExecution } from "../hooks/useExecutions";
import {
  executionOriginLabel,
  executionStatusMeta,
  executionTypeLabel,
} from "../lib/executions";
import { formatDate, formatDateTime, formatDuration } from "../lib/format";

function ExecutionTimeline({ job }: { job: Job }) {
  const steps = [
    { label: "Adicionada à fila", date: job.created_at, done: true },
    {
      label: "Execução iniciada",
      date: job.started_at,
      done: Boolean(job.started_at),
    },
    {
      label: job.status === "failed" ? "Encerrada com falha" : "Execução concluída",
      date: job.finished_at,
      done: Boolean(job.finished_at),
      failed: job.status === "failed",
    },
  ];
  return (
    <ol className="execution-timeline">
      {steps.map((step, index) => (
        <li
          className={`${step.done ? "timeline-done" : ""} ${step.failed ? "timeline-failed" : ""}`}
          key={step.label}
        >
          <span>{step.done ? <Icon name={step.failed ? "x" : "check"} /> : index + 1}</span>
          <div><strong>{step.label}</strong><small>{step.date ? formatDateTime(step.date) : "Aguardando"}</small></div>
        </li>
      ))}
    </ol>
  );
}

function EvaluationCard({ evaluation, index }: { evaluation: JobEvaluation; index: number }) {
  const notify = evaluation.decision.decision === "notify";
  return (
    <details className="evaluation-card">
      <summary>
        <span className={`evaluation-index ${notify ? "evaluation-notify" : ""}`}>
          {index + 1}
        </span>
        <span>
          <strong>{notify ? "Envio autorizado" : "Envio ignorado"}</strong>
          <small>Cobrança {evaluation.charge_id.slice(0, 8)} · {evaluation.decision.policy_name}</small>
        </span>
        <StatusBadge tone={notify ? "success" : "neutral"}>
          {notify ? "Notificar" : "Ignorar"}
        </StatusBadge>
        <Icon name="chevron-down" />
      </summary>
      <div className="evaluation-body">
        <dl className="technical-details">
          <div><dt>Motivo</dt><dd>{evaluation.decision.reason}</dd></div>
          <div><dt>Política selecionada</dt><dd>{evaluation.trace.selected_policy}</dd></div>
          <div><dt>Pipeline</dt><dd>{evaluation.trace.pipeline}</dd></div>
          <div><dt>Estratégia</dt><dd>{evaluation.trace.strategy}</dd></div>
          <div><dt>Duração do trace</dt><dd>{formatDuration(evaluation.trace.duration_ms)}</dd></div>
          <div>
            <dt>Cobrança</dt>
            <dd><Link to={`/cobrancas/${evaluation.charge_id}`}>Abrir cobrança</Link></dd>
          </div>
        </dl>
        <div className="trace-block">
          <h3>Políticas avaliadas</h3>
          <div className="trace-list">
            {evaluation.trace.evaluated.map((entry) => (
              <div className={entry.matched ? "trace-matched" : ""} key={entry.policy_name}>
                <Icon name={entry.matched ? "check" : "arrow-right"} />
                <span><strong>{entry.policy_name}</strong><small>{entry.reason ?? entry.outcome}</small></span>
                <b>{formatDuration(entry.duration_ms)}</b>
              </div>
            ))}
          </div>
        </div>
        {evaluation.trace.not_evaluated.length ? (
          <p className="not-evaluated">
            <strong>Não avaliadas após a decisão:</strong>{" "}
            {evaluation.trace.not_evaluated.join(", ")}
          </p>
        ) : null}
        {evaluation.notification ? (
          <div className="notification-result">
            <span><Icon name={evaluation.notification.error ? "x" : "check"} /></span>
            <div>
              <strong>Tentativa de notificação: {evaluation.notification.submission_status}</strong>
              <small>
                {evaluation.notification.deduplicated
                  ? "Envio deduplicado; nenhuma nova mensagem foi criada."
                  : evaluation.notification.error ?? `Tentativa ${evaluation.notification.attempt_id.slice(0, 8)}`}
              </small>
            </div>
          </div>
        ) : null}
      </div>
    </details>
  );
}

export function ExecutionDetailPage() {
  const { executionId = "" } = useParams();
  const execution = useExecution(executionId);

  if (execution.isLoading) return <div className="page-stack"><Skeleton lines={10} /></div>;
  if (execution.error || !execution.data) {
    return <ErrorState error={execution.error} onRetry={() => void execution.refetch()} />;
  }

  const job = execution.data;
  const meta = executionStatusMeta[job.status];
  const evaluations = job.result?.evaluations ?? [];
  return (
    <div className="page-stack entity-page execution-detail-page">
      <Link className="back-link" to="/fila">
        <Icon name="arrow-left" /> Voltar para execuções
      </Link>
      <PageHeader
        eyebrow="Inspeção técnica"
        title={executionTypeLabel[job.type]}
        description={`Execução ${job.id} criada em ${formatDateTime(job.created_at)}.`}
        actions={<StatusBadge tone={meta.tone}>{meta.label}</StatusBadge>}
      />
      {!job.terminal ? (
        <div className="feedback-banner execution-live" role="status">
          <i /> Acompanhando esta execução a cada 2 segundos.
        </div>
      ) : null}
      {job.error ? (
        <div className="execution-error" role="alert">
          <Icon name="x" />
          <div><strong>Erro da execução</strong><pre>{job.error}</pre></div>
        </div>
      ) : null}

      <section className="execution-overview-grid">
        <article className="surface-card execution-summary">
          <div className="section-heading"><div><span className="eyebrow">Ciclo de vida</span><h2>Linha do tempo</h2></div></div>
          <ExecutionTimeline job={job} />
        </article>
        <article className="surface-card execution-summary">
          <div className="section-heading"><div><span className="eyebrow">Execução</span><h2>Dados técnicos</h2></div></div>
          <dl className="technical-details">
            <div><dt>Origem</dt><dd>{executionOriginLabel[job.origin as keyof typeof executionOriginLabel] ?? job.origin}</dd></div>
            <div><dt>Tentativas</dt><dd>{job.attempts} de {job.max_attempts}</dd></div>
            <div><dt>Duração</dt><dd>{formatDuration(job.duration_ms)}</dd></div>
            <div><dt>Agendada para</dt><dd>{formatDateTime(job.scheduled_for)}</dd></div>
            <div><dt>Worker</dt><dd>{job.locked_by ?? "—"}</dd></div>
            <div><dt>Retém deduplicação</dt><dd>{job.retain_deduplication_key ? "Sim" : "Não"}</dd></div>
          </dl>
        </article>
      </section>

      {job.result ? (
        <section className="execution-result-grid">
          <article><strong>{job.result.evaluated}</strong><span>Avaliadas</span></article>
          <article><strong>{job.result.eligible}</strong><span>Elegíveis</span></article>
          <article><strong>{job.result.skipped}</strong><span>Ignoradas</span></article>
          <article><strong>{job.result.simulated}</strong><span>Simuladas</span></article>
          <article><strong>{job.result.deduplicated}</strong><span>Deduplicadas</span></article>
          <article><strong>{job.result.notification_failed}</strong><span>Falhas</span></article>
        </section>
      ) : null}

      <section className="surface-card execution-evaluations">
        <div className="section-heading">
          <div><span className="eyebrow">PolicyFlow</span><h2>Decisões e traces</h2></div>
          {job.result?.reference_date ? (
            <span className="section-caption">Referência: {formatDate(job.result.reference_date)}</span>
          ) : null}
        </div>
        {evaluations.length ? (
          <div className="evaluation-list">
            {evaluations.map((evaluation, index) => (
              <EvaluationCard evaluation={evaluation} index={index} key={evaluation.charge_id} />
            ))}
          </div>
        ) : (
          <div className="technical-empty">
            <Icon name={job.terminal ? "activity" : "clock"} />
            <span>
              {job.terminal
                ? "Esta execução terminou sem avaliações detalhadas."
                : "As decisões aparecerão quando o processamento terminar."}
            </span>
          </div>
        )}
      </section>
      <details className="surface-card raw-payload">
        <summary>Payload original <Icon name="chevron-down" /></summary>
        <pre>{JSON.stringify(job.payload, null, 2)}</pre>
      </details>
    </div>
  );
}
