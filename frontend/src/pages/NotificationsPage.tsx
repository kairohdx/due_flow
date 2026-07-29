import { Link, useSearchParams } from "react-router-dom";
import type {
  NotificationAttempt,
  NotificationProvider,
  NotificationSubmissionStatus,
  NotificationType,
} from "../api/types";
import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { DataTable, type TableColumn } from "../components/ui/DataTable";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { StatusBadge } from "../components/ui/StatusBadge";
import {
  useNotificationMetrics,
  useNotifications,
} from "../hooks/useNotifications";
import {
  notificationProviderLabel,
  notificationDeliveryMeta,
  notificationSubmissionMeta,
  notificationTypeLabel,
} from "../lib/notifications";
import { formatDateTime, formatPhone } from "../lib/format";

export function NotificationsPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const status = (params.get("status") || undefined) as NotificationSubmissionStatus | undefined;
  const provider = (params.get("provider") || undefined) as NotificationProvider | undefined;
  const type = (params.get("type") || undefined) as NotificationType | undefined;
  const notifications = useNotifications({ page, pageSize: 25, status, provider, type });
  const metrics = useNotificationMetrics();

  function updateParams(changes: Record<string, string | undefined>) {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    setParams(next);
  }

  const columns: TableColumn<NotificationAttempt>[] = [
    {
      key: "notification",
      label: "Notificação",
      render: (attempt) => (
        <Link className="cell-stack entity-primary" to={`/notificacoes/${attempt.id}`}>
          <strong>{notificationTypeLabel[attempt.notification_type]}</strong>
          <small>{attempt.message}</small>
        </Link>
      ),
    },
    {
      key: "destination",
      label: "Destino",
      render: (attempt) => formatPhone(attempt.destination),
    },
    {
      key: "provider",
      label: "Canal",
      render: (attempt) => notificationProviderLabel[attempt.provider],
    },
    {
      key: "processed",
      label: "Processada em",
      render: (attempt) => formatDateTime(attempt.processed_at),
    },
    {
      key: "submission",
      label: "Envio para a Meta",
      render: (attempt) => (
        <StatusBadge tone={notificationSubmissionMeta(attempt).tone}>
          {notificationSubmissionMeta(attempt).label}
        </StatusBadge>
      ),
    },
    {
      key: "delivery",
      label: "Entrega no WhatsApp",
      render: (attempt) => (
        <StatusBadge tone={notificationDeliveryMeta(attempt).tone}>
          {attempt.provider === "fake"
            ? "Não se aplica"
            : notificationDeliveryMeta(attempt).label}
        </StatusBadge>
      ),
    },
    {
      key: "action",
      label: "",
      align: "right",
      render: (attempt) => (
        <Link className="table-action" to={`/notificacoes/${attempt.id}`}>
          Ver tentativa <Icon name="arrow-right" />
        </Link>
      ),
    },
  ];
  const filtered = Boolean(status || provider || type);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Histórico de envios"
        title="Histórico de mensagens"
        description="Consulte mensagens simuladas, enviadas e com falha."
      />
      {metrics.data ? (
        <section className="notification-metrics" aria-label="Indicadores das mensagens">
          <article><strong>{metrics.data.submissions_succeeded_last_24h}</strong><span>Aceitos pela Meta</span><small>Últimas 24 horas</small></article>
          <article><strong>{metrics.data.submissions_failed_last_24h}</strong><span>Falhas no envio</span><small>Últimas 24 horas</small></article>
          <article><strong>{metrics.data.deliveries_awaiting}</strong><span>Aguardando retorno</span><small>Estado atual</small></article>
          <article><strong>{metrics.data.deliveries_confirmed_last_24h}</strong><span>Entregues</span><small>Últimas 24 horas</small></article>
          <article><strong>{metrics.data.deliveries_read_last_24h}</strong><span>Lidas</span><small>Últimas 24 horas</small></article>
          <article><strong>{metrics.data.deliveries_failed_last_24h}</strong><span>Falhas na entrega</span><small>Últimas 24 horas</small></article>
        </section>
      ) : null}
      <section className="surface-card list-card">
        <div className="list-toolbar notification-toolbar">
          <select
            aria-label="Filtrar resultado"
            value={status ?? ""}
            onChange={(event) =>
              updateParams({ status: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os resultados</option>
            <option value="simulated">Simuladas</option>
            <option value="succeeded">Aceitas pela Meta</option>
            <option value="failed">Com falha</option>
            <option value="unknown">Resultado incerto</option>
            <option value="pending">Aguardando</option>
          </select>
          <select
            aria-label="Filtrar canal"
            value={provider ?? ""}
            onChange={(event) =>
              updateParams({ provider: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os canais</option>
            <option value="fake">Simulador</option>
            <option value="meta">WhatsApp Meta</option>
          </select>
          <select
            aria-label="Filtrar tipo de mensagem"
            value={type ?? ""}
            onChange={(event) =>
              updateParams({ type: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os tipos</option>
            <option value="upcoming">Lembrete antecipado</option>
            <option value="due_today">Vencimento hoje</option>
            <option value="overdue">Cobrança vencida</option>
          </select>
        </div>
        {notifications.isLoading ? <Skeleton lines={8} /> : null}
        {notifications.error && !notifications.data ? (
          <ErrorState error={notifications.error} onRetry={() => void notifications.refetch()} />
        ) : null}
        {notifications.data?.total === 0 ? (
          <EmptyState
            icon="message"
            title={filtered ? "Nenhuma notificação encontrada" : "Nenhuma notificação registrada"}
            description={
              filtered
                ? "Tente remover os filtros para ampliar a busca."
                : "As tentativas de envio aparecerão aqui após as verificações."
            }
          />
        ) : null}
        {notifications.data?.items.length ? (
          <>
            <DataTable columns={columns} rows={notifications.data.items} rowKey={(item) => item.id} />
            <Pagination
              page={notifications.data.page}
              pages={notifications.data.pages}
              total={notifications.data.total}
              onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
            />
          </>
        ) : null}
      </section>
    </div>
  );
}
