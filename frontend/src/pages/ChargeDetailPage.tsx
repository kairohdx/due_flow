import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { userFacingError } from "../api/errors";
import { ChargeForm } from "../components/charges/ChargeForm";
import { ConfirmDialog } from "../components/feedback/ConfirmDialog";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { Button } from "../components/ui/Button";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import {
  useCancelCharge,
  useCharge,
  useMarkChargePaid,
  useProcessCharge,
  useUpdateCharge,
} from "../hooks/useCharges";
import { useCustomer } from "../hooks/useCustomers";
import {
  useChargeNotifications,
  useNotificationRetry,
} from "../hooks/useNotifications";
import { chargeDeadlineState, chargeStatusMeta } from "../lib/charges";
import { formatCurrency, formatDate, formatDateTime } from "../lib/format";
import {
  notificationProviderLabel,
  notificationResultMeta,
  notificationTypeLabel,
} from "../lib/notifications";

type Action = "paid" | "cancel" | "process" | null;

function ChargeRetryAction({ attemptId }: { attemptId: string }) {
  const retryFlow = useNotificationRetry(attemptId);
  if (
    !retryFlow.recovery.data?.eligible &&
    !retryFlow.recovery.data?.template_eligible
  ) return null;
  const withTemplate = retryFlow.recovery.data.template_eligible;
  return (
    <Button
      variant="secondary"
      icon={<Icon name="refresh" />}
      loading={
        retryFlow.retry.isPending ||
        retryFlow.retryTemplate.isPending ||
        Boolean(retryFlow.job.data && !retryFlow.job.data.terminal)
      }
      onClick={() =>
        withTemplate
          ? retryFlow.retryTemplate.mutate()
          : retryFlow.retry.mutate()
      }
    >
      {withTemplate ? "Reenviar com template" : "Tentar novamente"}
    </Button>
  );
}

export function ChargeDetailPage() {
  const { chargeId = "" } = useParams();
  const [editing, setEditing] = useState(false);
  const [action, setAction] = useState<Action>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const charge = useCharge(chargeId);
  const customer = useCustomer(charge.data?.customer_id ?? "");
  const update = useUpdateCharge(chargeId);
  const markPaid = useMarkChargePaid(chargeId);
  const cancel = useCancelCharge(chargeId);
  const process = useProcessCharge(chargeId);
  const notifications = useChargeNotifications(chargeId);

  if (charge.isLoading) return <div className="page-stack"><Skeleton lines={8} /></div>;
  if (charge.error || !charge.data) {
    return <ErrorState error={charge.error} onRetry={() => void charge.refetch()} />;
  }

  const data = charge.data;
  const pending = data.status === "pending";
  const deadline = chargeDeadlineState(
    data.status,
    data.due_date,
    data.reminder_days_before,
  );
  const actionError = markPaid.error ?? cancel.error ?? process.error;
  const busy = markPaid.isPending || cancel.isPending || process.isPending;

  function confirmAction() {
    if (action === "paid") {
      markPaid.mutate(undefined, {
        onSuccess: () => {
          setAction(null);
          setFeedback("Cobrança marcada como paga.");
        },
      });
    }
    if (action === "cancel") {
      cancel.mutate(undefined, {
        onSuccess: () => {
          setAction(null);
          setFeedback("Cobrança cancelada.");
        },
      });
    }
    if (action === "process") {
      process.mutate(undefined, {
        onSuccess: (job) => {
          setAction(null);
          setFeedback(
            job.created
              ? "Verificação adicionada à fila."
              : "Esta cobrança já está aguardando verificação.",
          );
        },
      });
    }
  }

  const dialogs = {
    paid: {
      title: "Marcar cobrança como paga?",
      description: "Ela deixará de ser elegível para novos lembretes.",
      confirmLabel: "Marcar como paga",
      danger: false,
    },
    cancel: {
      title: "Cancelar esta cobrança?",
      description: "A cobrança cancelada não poderá ser marcada como paga ou verificada.",
      confirmLabel: "Cancelar cobrança",
      danger: true,
    },
    process: {
      title: "Verificar cobrança agora?",
      description: "A cobrança será avaliada e uma mensagem será enviada somente se as regras permitirem.",
      confirmLabel: "Adicionar à fila",
      danger: false,
    },
  };
  const dialogContent = dialogs[action ?? "process"];

  return (
    <div className="page-stack entity-page">
      <Link className="back-link" to="/cobrancas">
        <Icon name="arrow-left" /> Voltar para cobranças
      </Link>
      <PageHeader
        eyebrow="Detalhe da cobrança"
        title={data.description}
        description={`Cadastrada em ${formatDateTime(data.created_at)}.`}
        actions={
          pending && !editing ? (
            <div className="page-actions">
              <Button variant="secondary" icon={<Icon name="settings" />} onClick={() => setEditing(true)}>
                Editar
              </Button>
              <Button icon={<Icon name="play" />} onClick={() => setAction("process")}>
                Verificar agora
              </Button>
            </div>
          ) : null
        }
      />
      {feedback ? <div className="feedback-banner feedback-success" role="status">{feedback}</div> : null}
      {actionError ? <div className="feedback-banner feedback-error" role="alert">{userFacingError(actionError)}</div> : null}

      {editing ? (
        <section className="surface-card form-card">
          <div className="form-card-heading">
            <span className="form-heading-icon"><Icon name="settings" /></span>
            <div><h2>Editar cobrança</h2><p>As alterações entram em vigor imediatamente.</p></div>
          </div>
          <ChargeForm
            initialValue={{
              customer_id: data.customer_id,
              description: data.description,
              amount: data.amount,
              due_date: data.due_date,
              reminder_days_before: data.reminder_days_before,
            }}
            error={update.error}
            loading={update.isPending}
            submitLabel="Salvar alterações"
            onCancel={() => setEditing(false)}
            onSubmit={(payload) =>
              update.mutate(payload, {
                onSuccess: () => {
                  setEditing(false);
                  setFeedback("Cobrança atualizada.");
                },
              })
            }
          />
        </section>
      ) : (
        <>
          <section className="charge-hero surface-card">
            <div><span className="eyebrow">Valor da cobrança</span><strong>{formatCurrency(data.amount)}</strong></div>
            <StatusBadge tone={chargeStatusMeta[data.status].tone}>
              {chargeStatusMeta[data.status].label}
            </StatusBadge>
          </section>
          <section className="customer-summary-grid">
            <article className="surface-card detail-card">
              <span className="detail-icon"><Icon name="users" /></span>
              <div>
                <small>Cliente</small>
                <strong><Link to={`/clientes/${data.customer_id}`}>{customer.data?.name ?? "Carregando cliente..."}</Link></strong>
              </div>
            </article>
            <article className={`surface-card detail-card deadline-card deadline-${deadline}`}>
              <span className="detail-icon"><Icon name="calendar" /></span>
              <div>
                <small>
                  {deadline === "overdue"
                    ? "Vencida desde"
                    : deadline === "today"
                      ? "Vence hoje"
                      : deadline === "upcoming"
                        ? "Próximo vencimento"
                        : "Vencimento"}
                </small>
                <strong>{formatDate(data.due_date)}</strong>
              </div>
            </article>
            <article className="surface-card detail-card">
              <span className="detail-icon"><Icon name="bell" /></span>
              <div><small>Antecedência</small><strong>{data.reminder_days_before} dias</strong></div>
            </article>
          </section>
          <section className="surface-card charge-notifications-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow">Rastreabilidade</span>
                <h2>Histórico de envios</h2>
              </div>
              <Link className="text-link" to={`/notificacoes`}>
                Ver histórico completo <Icon name="arrow-right" />
              </Link>
            </div>
            {notifications.isLoading ? <Skeleton lines={3} /> : null}
            {notifications.error && !notifications.data ? (
              <ErrorState
                error={notifications.error}
                onRetry={() => void notifications.refetch()}
              />
            ) : null}
            {notifications.data?.total === 0 ? (
              <div className="charge-notifications-empty">
                <Icon name="message" />
                <div>
                  <strong>Nenhum envio registrado</strong>
                  <small>
                    Quando esta cobrança gerar uma mensagem, o resultado
                    aparecerá aqui.
                  </small>
                </div>
              </div>
            ) : null}
            {notifications.data?.items.length ? (
              <div className="charge-notifications-list">
                {notifications.data.items.map((attempt) => {
                  const attemptStatus = notificationResultMeta(attempt);
                  return (
                    <div className="charge-notification-item" key={attempt.id}>
                      <Link
                        className="charge-notification-row"
                        to={`/notificacoes/${attempt.id}`}
                      >
                        <span
                          className={`provider-mark provider-${attempt.provider}`}
                        >
                          <Icon
                            name={attempt.provider === "meta" ? "message" : "sparkles"}
                          />
                        </span>
                        <div>
                          <strong>
                            {notificationTypeLabel[attempt.notification_type]}
                          </strong>
                          <small>
                            {notificationProviderLabel[attempt.provider]} ·{" "}
                            {formatDateTime(attempt.processed_at)}
                          </small>
                        </div>
                        <StatusBadge tone={attemptStatus.tone}>
                          {attemptStatus.label}
                        </StatusBadge>
                        <Icon name="arrow-right" />
                      </Link>
                      <ChargeRetryAction attemptId={attempt.id} />
                    </div>
                  );
                })}
              </div>
            ) : null}
          </section>
          {pending ? (
            <section className="surface-card resolution-card">
              <div>
                <span className="eyebrow">Resolver cobrança</span>
                <h2>Ações operacionais</h2>
                <p>Confirme o pagamento ou cancele uma cobrança que não deve mais receber lembretes.</p>
              </div>
              <div className="page-actions">
                <Button variant="secondary" icon={<Icon name="check" />} onClick={() => setAction("paid")}>
                  Marcar como paga
                </Button>
                <Button variant="danger" icon={<Icon name="x" />} onClick={() => setAction("cancel")}>
                  Cancelar cobrança
                </Button>
              </div>
            </section>
          ) : null}
        </>
      )}
      <ConfirmDialog
        open={action !== null}
        title={dialogContent.title}
        description={dialogContent.description}
        confirmLabel={dialogContent.confirmLabel}
        danger={dialogContent.danger}
        loading={busy}
        onCancel={() => !busy && setAction(null)}
        onConfirm={confirmAction}
      />
    </div>
  );
}
