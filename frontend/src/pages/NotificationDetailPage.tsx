import { Link, useParams } from "react-router-dom";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";
import { useCharge } from "../hooks/useCharges";
import { useCustomer } from "../hooks/useCustomers";
import {
  useNotification,
  useNotificationRetry,
} from "../hooks/useNotifications";
import { userFacingError } from "../api/errors";
import {
  notificationProviderLabel,
  notificationDeliveryMeta,
  notificationResultMeta,
  notificationSubmissionMeta,
  notificationTypeLabel,
} from "../lib/notifications";
import { formatDateTime, formatDuration, formatPhone } from "../lib/format";

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function NotificationDetailPage() {
  const { notificationId = "" } = useParams();
  const notification = useNotification(notificationId);
  const retryFlow = useNotificationRetry(notificationId);
  const charge = useCharge(notification.data?.charge_id ?? "");
  const customer = useCustomer(charge.data?.customer_id ?? "");

  if (notification.isLoading) return <div className="page-stack"><Skeleton lines={10} /></div>;
  if (notification.error || !notification.data) {
    return <ErrorState error={notification.error} onRetry={() => void notification.refetch()} />;
  }

  const attempt = notification.data;
  const status = notificationResultMeta(attempt);
  const submission = notificationSubmissionMeta(attempt);
  const delivery = notificationDeliveryMeta(attempt);
  const submissionFailed =
    attempt.submission_status === "failed" ||
    attempt.submission_status === "unknown";
  const deliveryFailed = attempt.delivery_status === "failed";
  const errorInfo =
    attempt.delivery_error_info ?? attempt.submission_error_info;
  const providerResponse = asRecord(attempt.provider_response);
  const safeResponse = asRecord(providerResponse?.response);
  const httpStatus =
    typeof safeResponse?.http_status === "number"
      ? safeResponse.http_status
      : null;
  const correlationId =
    typeof safeResponse?.correlation_id === "string"
      ? safeResponse.correlation_id
      : null;
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

      <section className="surface-card message-timeline" aria-label="Linha do tempo da mensagem">
        <div className="section-heading">
          <div><span className="eyebrow">Rastreabilidade</span><h2>Linha do tempo</h2></div>
        </div>
        <ol>
          <li className={submissionFailed ? "timeline-error" : "timeline-success"}>
            <span><Icon name={submissionFailed ? "x" : attempt.submission_status === "pending" ? "clock" : "check"} /></span>
            <div>
              <strong>
                {attempt.provider === "fake"
                  ? "Processamento no simulador"
                  : "Envio para a Meta"}{" "}
                · {submission.label}
              </strong>
              <small>
                {attempt.submission_error_details ??
                  (attempt.provider === "fake"
                    ? "Processamento concluído pelo simulador local."
                    : `Solicitação processada em ${formatDateTime(attempt.processed_at)}.`)}
              </small>
            </div>
          </li>
          {attempt.provider === "meta" || attempt.delivery_status !== "not_started" ? (
            <li className={deliveryFailed ? "timeline-error" : attempt.delivery_status === "delivered" || attempt.delivery_status === "read" ? "timeline-success" : "timeline-pending"}>
              <span><Icon name={deliveryFailed ? "x" : attempt.delivery_status === "pending" || attempt.delivery_status === "sent" ? "clock" : "check"} /></span>
              <div>
                <strong>
                  {attempt.provider === "fake"
                    ? "Entrega simulada"
                    : "Entrega no WhatsApp"}{" "}
                  · {delivery.label}
                </strong>
                <small>
                  {attempt.delivery_status === "not_started"
                    ? "A entrega não foi iniciada porque o envio não foi confirmado."
                    : attempt.delivery_event_at
                      ? `Atualizada em ${formatDateTime(attempt.delivery_event_at)}.`
                      : attempt.provider === "fake"
                        ? "Aguardando o próximo ciclo do simulador."
                        : "Aguardando uma atualização do WhatsApp."}
                </small>
              </div>
            </li>
          ) : null}
        </ol>
      </section>

      <section className={`surface-card provider-audit provider-audit-${attempt.provider}`}>
        <span className="provider-audit-icon">
          <Icon name={attempt.provider === "meta" ? "message" : "sparkles"} />
        </span>
        <div className="provider-audit-copy">
          <span className="eyebrow">Origem do envio</span>
          <h2>
            {attempt.provider === "meta"
              ? "WhatsApp Cloud API da Meta"
              : "Simulador local"}
          </h2>
          <p>
            {attempt.provider === "meta"
              ? submissionFailed
                ? "A solicitação não teve o aceite confirmado pela Meta; nenhuma entrega foi iniciada."
                : deliveryFailed
                ? "A Meta aceitou a requisição inicial, mas confirmou que a mensagem não foi entregue."
                : attempt.delivery_status === "delivered" ||
                    attempt.delivery_status === "read"
                  ? "A Meta confirmou a entrega desta mensagem ao destinatário."
                  : "A API da Meta aceitou a mensagem e devolveu um identificador."
              : deliveryFailed
                ? "Nenhuma requisição externa foi realizada; o simulador reproduziu uma falha de entrega."
                : attempt.delivery_status === "delivered" ||
                    attempt.delivery_status === "read"
                  ? "Nenhuma requisição externa foi realizada; o simulador confirmou a entrega fictícia."
                  : "Nenhuma requisição externa foi realizada; o retorno fictício será atualizado pelo worker."}
          </p>
        </div>
        <dl className="provider-audit-facts">
          <div>
            <dt>Modo</dt>
            <dd>{attempt.provider === "meta" ? "Real" : "Simulado"}</dd>
          </div>
          <div>
            <dt>{attempt.provider === "fake" ? "Processamento" : "Envio para a Meta"}</dt>
            <dd>{submission.label}</dd>
          </div>
          <div>
            <dt>{attempt.provider === "fake" ? "Entrega simulada" : "Entrega no WhatsApp"}</dt>
            <dd>{delivery.label}</dd>
          </div>
          {httpStatus !== null ? (
            <div><dt>HTTP</dt><dd>{httpStatus}</dd></div>
          ) : null}
          <div>
            <dt>ID da mensagem</dt>
            <dd>{attempt.provider_message_id ?? "Não informado"}</dd>
          </div>
          {correlationId ? (
            <div><dt>Correlação</dt><dd>{correlationId}</dd></div>
          ) : null}
          {attempt.delivery_error_code ? (
            <div><dt>{attempt.provider === "fake" ? "Código simulado" : "Código Meta"}</dt><dd>{attempt.delivery_error_code}</dd></div>
          ) : null}
        </dl>
      </section>

      {errorInfo ? (
        <section className="surface-card delivery-error-card" role="alert">
          <span><Icon name="x" /></span>
          <div>
            <span className="eyebrow">
              {deliveryFailed
                ? "Falha na entrega"
                : attempt.provider === "fake"
                  ? "Falha no simulador"
                  : "Falha no envio para a Meta"}
            </span>
            <h2>{errorInfo.title}</h2>
            <p>{errorInfo.message}</p>
            <strong className="error-recommended-action">{errorInfo.action}</strong>
            {errorInfo.code ? (
              <small>Código Meta {errorInfo.code}</small>
            ) : null}
            {!errorInfo.known ? <small>Erro ainda não catalogado.</small> : null}
            {errorInfo.technical_title || errorInfo.technical_details ? (
              <details className="error-technical-details">
                <summary>Detalhes técnicos</summary>
                {errorInfo.technical_title ? <p>{errorInfo.technical_title}</p> : null}
                {errorInfo.technical_details ? <p>{errorInfo.technical_details}</p> : null}
              </details>
            ) : null}
          </div>
        </section>
      ) : null}

      {retryFlow.recovery.data ? (
        <section className={`surface-card recovery-card recovery-${retryFlow.recovery.data.action}`}>
          <div>
            <span className="eyebrow">Próxima ação</span>
            <h2>
              {retryFlow.recovery.data.eligible
                ? "Esta mensagem pode ser reenviada"
                : retryFlow.recovery.data.action === "template"
                  ? "Esta falha exige um template aprovado"
                  : retryFlow.recovery.data.action === "fix"
                    ? "Corrija os dados antes de reenviar"
                    : retryFlow.recovery.data.action === "review"
                      ? "Revise esta falha antes de reenviar"
                      : "Retentativa indisponível"}
            </h2>
            <p>
              {retryFlow.recovery.data.eligible
                ? "O reenvio criará uma nova tentativa e preservará todo o histórico atual."
                : retryFlow.recovery.data.action === "template"
                  ? retryFlow.recovery.data.template_eligible
                    ? "Repetir o texto livre provavelmente causaria a mesma falha. O novo envio usará o template configurado e preservará o histórico."
                    : "Repetir o texto livre provavelmente causaria a mesma falha. Configure um template aprovado para continuar."
                  : `Motivo técnico: ${retryFlow.recovery.data.reason}.`}
            </p>
          </div>
          {retryFlow.recovery.data.eligible ? (
            <Button
              icon={<Icon name="refresh" />}
              loading={retryFlow.retry.isPending || Boolean(retryFlow.job.data && !retryFlow.job.data.terminal)}
              onClick={() => retryFlow.retry.mutate()}
            >
              Tentar novamente
            </Button>
          ) : retryFlow.recovery.data.template_eligible ? (
            <Button
              icon={<Icon name="message" />}
              loading={
                retryFlow.retryTemplate.isPending ||
                Boolean(retryFlow.job.data && !retryFlow.job.data.terminal)
              }
              onClick={() => retryFlow.retryTemplate.mutate()}
            >
              Reenviar com template
            </Button>
          ) : null}
          {retryFlow.retry.error || retryFlow.retryTemplate.error ? (
            <div className="inline-error" role="alert">
              {userFacingError(
                retryFlow.retry.error ?? retryFlow.retryTemplate.error,
              )}
            </div>
          ) : null}
          {retryFlow.job.data?.terminal ? (
            <StatusBadge tone={retryFlow.job.data.result?.retried ? "success" : "warning"}>
              {retryFlow.job.data.result?.retried
                ? "Nova tentativa criada"
                : "Retentativa cancelada"}
            </StatusBadge>
          ) : null}
        </section>
      ) : null}

      {retryFlow.attempts.data && retryFlow.attempts.data.length > 1 ? (
        <section className="surface-card attempt-family-card">
          <div className="section-heading">
            <div><span className="eyebrow">Histórico preservado</span><h2>Tentativas relacionadas</h2></div>
          </div>
          <div className="attempt-family-list">
            {retryFlow.attempts.data.map((item) => {
              const itemStatus = notificationResultMeta(item);
              return (
                <Link key={item.id} to={`/notificacoes/${item.id}`}>
                  <span>Tentativa {item.attempt_number ?? 1}</span>
                  <small>{formatDateTime(item.processed_at)}</small>
                  <StatusBadge tone={itemStatus.tone}>{itemStatus.label}</StatusBadge>
                  <Icon name="arrow-right" />
                </Link>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="notification-overview-grid">
        <article className="surface-card notification-message-card">
          <div className="section-heading">
            <div><span className="eyebrow">Conteúdo</span><h2>Mensagem</h2></div>
          </div>
          <blockquote>{attempt.message}</blockquote>
          <dl className="technical-details">
            <div>
              <dt>Formato</dt>
              <dd>{attempt.message_format === "template" ? "Template configurado" : "Texto livre"}</dd>
            </div>
            {attempt.template_info ? (
              <>
                <div><dt>Template</dt><dd>{attempt.template_info.name}</dd></div>
                <div><dt>Idioma</dt><dd>{attempt.template_info.language}</dd></div>
              </>
            ) : null}
            <div><dt>Destino</dt><dd>{formatPhone(attempt.destination)}</dd></div>
            <div><dt>Provider utilizado</dt><dd>{notificationProviderLabel[attempt.provider]}</dd></div>
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
          <summary>Dados técnicos sanitizados <Icon name="chevron-down" /></summary>
          <pre>{JSON.stringify(attempt.provider_response, null, 2)}</pre>
        </details>
      ) : null}
      {attempt.delivery_response ? (
        <details className="surface-card raw-payload">
          <summary>Evento de entrega sanitizado <Icon name="chevron-down" /></summary>
          <pre>{JSON.stringify(attempt.delivery_response, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}
