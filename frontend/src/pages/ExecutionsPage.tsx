import { Link, useSearchParams } from "react-router-dom";
import type { Job, JobOrigin, JobStatus, JobType } from "../api/types";
import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { DataTable, type TableColumn } from "../components/ui/DataTable";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useExecutions } from "../hooks/useExecutions";
import {
  executionOriginLabel,
  executionStatusMeta,
  executionTypeLabel,
} from "../lib/executions";
import { formatDateTime, formatDuration } from "../lib/format";

export function ExecutionsPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const status = (params.get("status") || undefined) as JobStatus | undefined;
  const origin = (params.get("origin") || undefined) as JobOrigin | undefined;
  const type = (params.get("type") || undefined) as JobType | undefined;
  const executions = useExecutions({ page, pageSize: 25, status, origin, type });
  const hasActive = executions.data?.items.some(
    (item) => item.status === "queued" || item.status === "processing",
  );

  function updateParams(changes: Record<string, string | undefined>) {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    setParams(next);
  }

  const columns: TableColumn<Job>[] = [
    {
      key: "execution",
      label: "Execução",
      render: (job) => (
        <Link className="cell-stack entity-primary" to={`/fila/${job.id}`}>
          <strong>{executionTypeLabel[job.type]}</strong>
          <small>{job.id.slice(0, 8)} · {formatDateTime(job.created_at)}</small>
        </Link>
      ),
    },
    {
      key: "origin",
      label: "Origem",
      render: (job) =>
        executionOriginLabel[job.origin as JobOrigin] ?? job.origin,
    },
    {
      key: "attempts",
      label: "Tentativas",
      render: (job) => `${job.attempts} de ${job.max_attempts}`,
    },
    {
      key: "duration",
      label: "Duração",
      render: (job) => formatDuration(job.duration_ms),
    },
    {
      key: "status",
      label: "Estado",
      render: (job) => (
        <StatusBadge tone={executionStatusMeta[job.status].tone}>
          {executionStatusMeta[job.status].label}
        </StatusBadge>
      ),
    },
    {
      key: "action",
      label: "",
      align: "right",
      render: (job) => (
        <Link className="table-action" to={`/fila/${job.id}`}>
          Inspecionar <Icon name="arrow-right" />
        </Link>
      ),
    },
  ];
  const filtered = Boolean(status || origin || type);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Diagnóstico avançado"
        title="Execuções da automação"
        description="Acompanhe a fila, tentativas e resultados técnicos de cada verificação."
        actions={
          <div className={`polling-indicator ${hasActive ? "polling-active" : ""}`}>
            <i />
            {hasActive ? "Atualizando a cada 2s" : "Fila estável"}
          </div>
        }
      />
      <section className="surface-card list-card">
        <div className="list-toolbar execution-toolbar">
          <select
            aria-label="Filtrar estado"
            value={status ?? ""}
            onChange={(event) =>
              updateParams({ status: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os estados</option>
            <option value="queued">Aguardando</option>
            <option value="processing">Em execução</option>
            <option value="completed">Concluídas</option>
            <option value="failed">Com falha</option>
          </select>
          <select
            aria-label="Filtrar origem"
            value={origin ?? ""}
            onChange={(event) =>
              updateParams({ origin: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todas as origens</option>
            <option value="automatic">Automáticas</option>
            <option value="manual">Manuais</option>
          </select>
          <select
            aria-label="Filtrar tipo"
            value={type ?? ""}
            onChange={(event) =>
              updateParams({ type: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os tipos</option>
            <option value="process_due_charges">Verificação geral</option>
            <option value="process_charge">Cobrança individual</option>
          </select>
        </div>
        {executions.isLoading ? <Skeleton lines={8} /> : null}
        {executions.error && !executions.data ? (
          <ErrorState error={executions.error} onRetry={() => void executions.refetch()} />
        ) : null}
        {executions.data?.total === 0 ? (
          <EmptyState
            icon="activity"
            title={filtered ? "Nenhuma execução encontrada" : "Nenhuma execução registrada"}
            description={
              filtered
                ? "Tente remover os filtros para ampliar a busca."
                : "As verificações manuais e automáticas aparecerão aqui."
            }
          />
        ) : null}
        {executions.data?.items.length ? (
          <>
            <DataTable columns={columns} rows={executions.data.items} rowKey={(job) => job.id} />
            <Pagination
              page={executions.data.page}
              pages={executions.data.pages}
              total={executions.data.total}
              onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
            />
          </>
        ) : null}
      </section>
    </div>
  );
}
