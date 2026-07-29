import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { Charge, ChargeStatus } from "../api/types";
import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { DataTable, type TableColumn } from "../components/ui/DataTable";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useCharges } from "../hooks/useCharges";
import { chargeDeadlineState, chargeStatusMeta } from "../lib/charges";
import { formatCurrency, formatDate } from "../lib/format";

export function ChargesPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const search = params.get("search") ?? "";
  const status = (params.get("status") || undefined) as ChargeStatus | undefined;
  const dueFrom = params.get("due_from") || undefined;
  const dueTo = params.get("due_to") || undefined;
  const [searchInput, setSearchInput] = useState(search);
  const charges = useCharges({
    page,
    pageSize: 25,
    search: search || undefined,
    status,
    dueFrom,
    dueTo,
  });

  function updateParams(changes: Record<string, string | undefined>) {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    setParams(next);
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    updateParams({ search: searchInput.trim() || undefined, page: undefined });
  }

  const columns: TableColumn<Charge>[] = [
    {
      key: "description",
      label: "Cobrança",
      render: (charge) => {
        const deadline = chargeDeadlineState(
          charge.status,
          charge.due_date,
          charge.reminder_days_before,
        );
        return (
          <Link className="cell-stack entity-primary" to={`/cobrancas/${charge.id}`}>
            <strong>{charge.description}</strong>
            <small className={`charge-deadline deadline-${deadline}`}>
              {deadline === "overdue"
                ? "Vencida em"
                : deadline === "today"
                  ? "Vence hoje ·"
                  : "Vence em"}{" "}
              {formatDate(charge.due_date)}
            </small>
          </Link>
        );
      },
    },
    { key: "amount", label: "Valor", render: (charge) => formatCurrency(charge.amount) },
    {
      key: "status",
      label: "Estado",
      render: (charge) => (
        <StatusBadge tone={chargeStatusMeta[charge.status].tone}>
          {chargeStatusMeta[charge.status].label}
        </StatusBadge>
      ),
    },
    {
      key: "action",
      label: "",
      align: "right",
      render: (charge) => (
        <Link className="table-action" to={`/cobrancas/${charge.id}`}>
          Ver detalhes <Icon name="arrow-right" />
        </Link>
      ),
    },
  ];
  const filtered = Boolean(search || status || dueFrom || dueTo);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Contas a receber"
        title="Cobranças"
        description="Cadastre vencimentos e acompanhe cada cobrança até sua resolução."
        actions={
          <Link className="button button-primary" to="/cobrancas/nova">
            <Icon name="credit-card" /> <span>Nova cobrança</span>
          </Link>
        }
      />
      <section className="surface-card list-card">
        <div className="list-toolbar charge-toolbar">
          <form className="search-box" onSubmit={submitSearch}>
            <Icon name="search" />
            <input
              aria-label="Buscar cobranças"
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Buscar pela descrição"
              value={searchInput}
            />
            {searchInput ? (
              <button
                aria-label="Limpar busca"
                type="button"
                onClick={() => {
                  setSearchInput("");
                  updateParams({ search: undefined, page: undefined });
                }}
              ><Icon name="x" /></button>
            ) : null}
          </form>
          <select
            aria-label="Filtrar estado"
            value={status ?? ""}
            onChange={(event) =>
              updateParams({ status: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os estados</option>
            <option value="pending">Em aberto</option>
            <option value="paid">Pagas</option>
            <option value="canceled">Canceladas</option>
          </select>
          <label className="compact-date">De
            <input
              aria-label="Vencimento inicial"
              type="date"
              value={dueFrom ?? ""}
              onChange={(event) =>
                updateParams({ due_from: event.target.value || undefined, page: undefined })
              }
            />
          </label>
          <label className="compact-date">Até
            <input
              aria-label="Vencimento final"
              type="date"
              value={dueTo ?? ""}
              onChange={(event) =>
                updateParams({ due_to: event.target.value || undefined, page: undefined })
              }
            />
          </label>
        </div>
        {charges.isLoading ? <Skeleton lines={7} /> : null}
        {charges.error && !charges.data ? (
          <ErrorState error={charges.error} onRetry={() => void charges.refetch()} />
        ) : null}
        {charges.data?.total === 0 ? (
          <EmptyState
            icon="credit-card"
            title={filtered ? "Nenhuma cobrança encontrada" : "Nenhuma cobrança cadastrada"}
            description={
              filtered
                ? "Tente remover os filtros ou buscar outro termo."
                : "Cadastre a primeira cobrança para iniciar o acompanhamento."
            }
            action={
              <Link className="button button-primary" to="/cobrancas/nova">
                Cadastrar cobrança
              </Link>
            }
          />
        ) : null}
        {charges.data?.items.length ? (
          <>
            <DataTable columns={columns} rows={charges.data.items} rowKey={(item) => item.id} />
            <Pagination
              page={charges.data.page}
              pages={charges.data.pages}
              total={charges.data.total}
              onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
            />
          </>
        ) : null}
      </section>
    </div>
  );
}
