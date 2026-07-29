import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import type { Charge, ChargeStatus } from "../api/types";
import { CustomerForm } from "../components/customers/CustomerForm";
import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { Skeleton } from "../components/feedback/Skeleton";
import { Button } from "../components/ui/Button";
import { DataTable, type TableColumn } from "../components/ui/DataTable";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { StatusBadge, type BadgeTone } from "../components/ui/StatusBadge";
import {
  useCustomer,
  useCustomerCharges,
  useUpdateCustomer,
} from "../hooks/useCustomers";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPhone,
} from "../lib/format";

const chargeStatus: Record<
  ChargeStatus,
  { label: string; tone: BadgeTone }
> = {
  pending: { label: "Pendente", tone: "warning" },
  paid: { label: "Paga", tone: "success" },
  canceled: { label: "Cancelada", tone: "neutral" },
};

const chargeColumns: TableColumn<Charge>[] = [
  {
    key: "description",
    label: "Cobrança",
    render: (charge) => (
      <span className="cell-stack">
        <strong>{charge.description}</strong>
        <small>Vence em {formatDate(charge.due_date)}</small>
      </span>
    ),
  },
  {
    key: "amount",
    label: "Valor",
    render: (charge) => formatCurrency(charge.amount),
  },
  {
    key: "status",
    label: "Situação",
    render: (charge) => (
      <StatusBadge tone={chargeStatus[charge.status].tone}>
        {chargeStatus[charge.status].label}
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

export function CustomerDetailPage() {
  const { customerId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const chargesPage = Math.max(1, Number(params.get("charges_page")) || 1);
  const [editing, setEditing] = useState(false);
  const customer = useCustomer(customerId);
  const charges = useCustomerCharges(customerId, chargesPage);
  const update = useUpdateCustomer(customerId);

  if (customer.isLoading) {
    return <div className="page-stack"><Skeleton lines={8} /></div>;
  }
  if (customer.error || !customer.data) {
    return (
      <ErrorState
        error={customer.error}
        onRetry={() => void customer.refetch()}
      />
    );
  }

  const data = customer.data;
  return (
    <div className="page-stack entity-page">
      <Link className="back-link" to="/clientes">
        <Icon name="arrow-left" /> Voltar para clientes
      </Link>
      <PageHeader
        eyebrow="Detalhe do cliente"
        title={data.name}
        description={`Cliente cadastrado em ${formatDateTime(data.created_at)}.`}
        actions={
          !editing ? (
            <Button
              variant="secondary"
              icon={<Icon name="settings" />}
              onClick={() => setEditing(true)}
            >
              Editar cliente
            </Button>
          ) : null
        }
      />

      {editing ? (
        <section className="surface-card form-card">
          <div className="form-card-heading">
            <span className="form-heading-icon"><Icon name="settings" /></span>
            <div><h2>Editar informações</h2><p>As alterações entram em vigor imediatamente.</p></div>
          </div>
          <CustomerForm
            initialValue={{
              name: data.name,
              phone: data.phone,
              active: data.active,
            }}
            error={update.error}
            loading={update.isPending}
            submitLabel="Salvar alterações"
            onCancel={() => setEditing(false)}
            onSubmit={(payload) =>
              update.mutate(payload, { onSuccess: () => setEditing(false) })
            }
          />
        </section>
      ) : (
        <section className="customer-summary-grid">
          <article className="surface-card customer-profile-card">
            <span className="customer-profile-avatar">
              {data.name.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <h2>{data.name}</h2>
              <StatusBadge tone={data.active ? "success" : "neutral"}>
                {data.active ? "Cliente ativo" : "Cliente inativo"}
              </StatusBadge>
            </div>
          </article>
          <article className="surface-card detail-card">
            <span className="detail-icon"><Icon name="bell" /></span>
            <div><small>WhatsApp</small><strong>{formatPhone(data.phone)}</strong></div>
          </article>
          <article className="surface-card detail-card">
            <span className="detail-icon"><Icon name="calendar" /></span>
            <div><small>Última atualização</small><strong>{formatDateTime(data.updated_at)}</strong></div>
          </article>
        </section>
      )}

      <section className="surface-card list-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Relacionamento</span>
            <h2>Cobranças deste cliente</h2>
          </div>
          {charges.data ? (
            <StatusBadge tone="info">{charges.data.total} no total</StatusBadge>
          ) : null}
        </div>
        {charges.isLoading ? <Skeleton lines={5} /> : null}
        {charges.error && !charges.data ? <ErrorState error={charges.error} /> : null}
        {charges.data?.total === 0 ? (
          <EmptyState
            icon="credit-card"
            title="Nenhuma cobrança cadastrada"
            description="Cadastre uma cobrança para iniciar o acompanhamento."
            action={
              <Link
                className="button button-primary"
                to={`/cobrancas/nova?customer_id=${data.id}`}
              >
                Nova cobrança
              </Link>
            }
          />
        ) : null}
        {charges.data?.items.length ? (
          <>
            <DataTable
              columns={chargeColumns}
              rows={charges.data.items}
              rowKey={(charge) => charge.id}
            />
            <Pagination
              page={charges.data.page}
              pages={charges.data.pages}
              total={charges.data.total}
              onPageChange={(page) => {
                const next = new URLSearchParams(params);
                if (page === 1) next.delete("charges_page");
                else next.set("charges_page", String(page));
                setParams(next);
              }}
            />
          </>
        ) : null}
      </section>
    </div>
  );
}
