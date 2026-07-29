import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { Customer } from "../api/types";
import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { DataTable, type TableColumn } from "../components/ui/DataTable";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useCustomers } from "../hooks/useCustomers";
import { formatDateTime, formatPhone } from "../lib/format";

const columns: TableColumn<Customer>[] = [
  {
    key: "name",
    label: "Cliente",
    render: (customer) => (
      <Link className="entity-primary" to={`/clientes/${customer.id}`}>
        <span className="customer-mini-avatar">
          {customer.name.slice(0, 2).toUpperCase()}
        </span>
        <span><strong>{customer.name}</strong><small>{formatPhone(customer.phone)}</small></span>
      </Link>
    ),
  },
  {
    key: "status",
    label: "Situação",
    render: (customer) => (
      <StatusBadge tone={customer.active ? "success" : "neutral"}>
        {customer.active ? "Ativo" : "Inativo"}
      </StatusBadge>
    ),
  },
  {
    key: "created",
    label: "Cadastrado em",
    render: (customer) => formatDateTime(customer.created_at),
  },
  {
    key: "action",
    label: "",
    align: "right",
    render: (customer) => (
      <Link className="table-action" to={`/clientes/${customer.id}`}>
        Ver detalhes <Icon name="arrow-right" />
      </Link>
    ),
  },
];

export function CustomersPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const search = params.get("search") ?? "";
  const activeParam = params.get("active");
  const active =
    activeParam === "true" ? true : activeParam === "false" ? false : undefined;
  const [searchInput, setSearchInput] = useState(search);
  const customers = useCustomers({ page, pageSize: 25, search: search || undefined, active });

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

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Base de contatos"
        title="Clientes"
        description="Gerencie quem recebe as cobranças e acompanhe sua situação."
        actions={
          <Link className="button button-primary" to="/clientes/novo">
            <Icon name="users" /> <span>Novo cliente</span>
          </Link>
        }
      />
      <section className="surface-card list-card">
        <div className="list-toolbar">
          <form className="search-box" onSubmit={submitSearch}>
            <Icon name="search" />
            <input
              aria-label="Buscar clientes"
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Buscar por nome ou telefone"
              value={searchInput}
            />
            {searchInput ? (
              <button
                type="button"
                aria-label="Limpar busca"
                onClick={() => {
                  setSearchInput("");
                  updateParams({ search: undefined, page: undefined });
                }}
              >
                <Icon name="x" />
              </button>
            ) : null}
          </form>
          <select
            aria-label="Filtrar situação"
            value={activeParam ?? ""}
            onChange={(event) =>
              updateParams({ active: event.target.value || undefined, page: undefined })
            }
          >
            <option value="">Todos os clientes</option>
            <option value="true">Somente ativos</option>
            <option value="false">Somente inativos</option>
          </select>
        </div>

        {customers.isLoading ? <Skeleton lines={7} /> : null}
        {customers.error && !customers.data ? (
          <ErrorState error={customers.error} onRetry={() => void customers.refetch()} />
        ) : null}
        {customers.data?.total === 0 ? (
          <EmptyState
            icon="users"
            title={search || activeParam ? "Nenhum cliente encontrado" : "Sua base começa aqui"}
            description={
              search || activeParam
                ? "Tente remover os filtros ou buscar outro termo."
                : "Cadastre o primeiro cliente para começar a criar cobranças."
            }
            action={
              <Link className="button button-primary" to="/clientes/novo">
                Cadastrar cliente
              </Link>
            }
          />
        ) : null}
        {customers.data?.items.length ? (
          <>
            <DataTable
              columns={columns}
              rows={customers.data.items}
              rowKey={(customer) => customer.id}
            />
            <Pagination
              page={customers.data.page}
              pages={customers.data.pages}
              total={customers.data.total}
              onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
            />
          </>
        ) : null}
      </section>
    </div>
  );
}
