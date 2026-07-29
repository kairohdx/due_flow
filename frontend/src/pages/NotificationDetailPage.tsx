import { Link, useParams } from "react-router-dom";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useCharge } from "../hooks/useCharges";
import { useCustomer } from "../hooks/useCustomers";
import { useNotification } from "../hooks/useNotifications";
import {
  notificationProviderLabel,
  notificationStatusMeta,
  notificationTypeLabel,
} from "../lib/notifications";
import { formatDateTime, formatDuration, formatPhone } from "../lib/format";

export function NotificationDetailPage() {
  const { notificationId = "" } = useParams();
  const notification = useNotification(notificationId);
  const charge = useCharge(notification.data?.charge_id ?? "");
  const customer = useCustomer(charge.data?.customer_id ?? "");

  if (notification.isLoading) return <div className="page-stack"><Skeleton lines={10} /></div>;
  if (notification.error || !notification.data) {
    return <ErrorState error={notification.error} onRetry={() => void notification.refetch()} />;
  }

  const attempt = notification.data;
  const status = notificationStatusMeta[attempt.status];
  return (
    <div className="page-stack entity-page notification-detail-page">
      <Link className="back-link" to="/notificacoes">
        <Icon name="arrow-left" /> Voltar para o histórico de mensagens
      </Link>
      <PageHeader
        eyebrow="Detalhe da tentativa"
        title={notificationTypeLabel[attempt.notification_type]}
        description={`Processada em ${formatDateTime(attempt.processed_at)}.`}
        actions={<StatusBadge tone={status.tone}>{status.label}</StatusBadge>}
      />

      <section className={`notification-delivery delivery-${attempt.status}`}>
        <span><Icon name={attempt.status === "failed" ? "x" : attempt.status === "pending" ? "clock" : "check"} /></span>
        <div>
          <strong>
            {attempt.status === "simulated"
              ? "Envio simulado com sucesso"
              : attempt.status === "sent"
                ? "Mensagem enviada"
                : attempt.status === "failed"
                  ? "Falha no envio"
                  : "Aguardando confirmação"}
          </strong>
          <small>
            {attempt.error ??
              `${notificationProviderLabel[attempt.provider]} · ${formatPhone(attempt.destination)}`}
          </small>
        </div>
      </section>

      <section className="notification-overview-grid">
        <article className="surface-card notification-message-card">
          <div className="section-heading">
            <div><span className="eyebrow">Conteúdo</span><h2>Mensagem</h2></div>
          </div>
          <blockquote>{attempt.message}</blockquote>
          <dl className="technical-details">
            <div><dt>Destino</dt><dd>{formatPhone(attempt.destination)}</dd></div>
            <div><dt>Canal</dt><dd>{notificationProviderLabel[attempt.provider]}</dd></div>
            <div><dt>ID do provider</dt><dd>{attempt.provider_message_id ?? "—"}</dd></div>
          </dl>
        </article>
        <article className="surface-card notification-links-card">
          <div className="section-heading">
            <div><span className="eyebrow">Relacionamentos</span><h2>Itens vinculados</h2></div>
          </div>
          <div className="notification-links">
            <Link to={`/cobrancas/${attempt.charge_id}`}>
              <span><Icon name="credit-card" /></span>
              <div><strong>{charge.data?.description ?? "Carregando cobrança..."}</strong><small>Abrir cobrança</small></div>
              <Icon name="arrow-right" />
            </Link>
            {customer.data ? (
              <Link to={`/clientes/${customer.data.id}`}>
                <span><Icon name="users" /></span>
                <div><strong>{customer.data.name}</strong><small>Abrir cliente</small></div>
                <Icon name="arrow-right" />
              </Link>
            ) : null}
            {attempt.processing_job_id ? (
              <Link to={`/fila/${attempt.processing_job_id}`}>
                <span><Icon name="activity" /></span>
                <div><strong>Execução {attempt.processing_job_id.slice(0, 8)}</strong><small>Inspecionar automação</small></div>
                <Icon name="arrow-right" />
              </Link>
            ) : null}
          </div>
        </article>
      </section>

      <section className="surface-card notification-policy-card">
        <div className="section-heading">
          <div><span className="eyebrow">Decisão</span><h2>Política e rastreabilidade</h2></div>
        </div>
        <dl className="technical-details">
          <div><dt>Política</dt><dd>{attempt.policy_name}</dd></div>
          <div><dt>Motivo</dt><dd>{attempt.decision_reason}</dd></div>
          <div><dt>Chave de idempotência</dt><dd>{attempt.idempotency_key}</dd></div>
          {attempt.trace ? (
            <>
              <div><dt>Trace ID</dt><dd>{attempt.trace.trace_id}</dd></div>
              <div><dt>Estratégia</dt><dd>{attempt.trace.strategy}</dd></div>
              <div><dt>Duração</dt><dd>{formatDuration(attempt.trace.duration_ms)}</dd></div>
            </>
          ) : null}
        </dl>
      </section>

      {attempt.provider_response ? (
        <details className="surface-card raw-payload">
          <summary>Resposta do provider <Icon name="chevron-down" /></summary>
          <pre>{JSON.stringify(attempt.provider_response, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}
