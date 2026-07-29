import { Link, useNavigate } from "react-router-dom";
import { CustomerForm } from "../components/customers/CustomerForm";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { useCreateCustomer } from "../hooks/useCustomers";

export function CustomerCreatePage() {
  const navigate = useNavigate();
  const create = useCreateCustomer();

  return (
    <div className="page-stack entity-page">
      <Link className="back-link" to="/clientes">
        <Icon name="arrow-left" /> Voltar para clientes
      </Link>
      <PageHeader
        eyebrow="Novo cadastro"
        title="Cadastrar cliente"
        description="Adicione os dados usados para identificar e enviar lembretes."
      />
      <section className="surface-card form-card">
        <div className="form-card-heading">
          <span className="form-heading-icon"><Icon name="users" /></span>
          <div>
            <h2>Informações do cliente</h2>
            <p>Você poderá editar estes dados depois.</p>
          </div>
        </div>
        <CustomerForm
          error={create.error}
          loading={create.isPending}
          submitLabel="Cadastrar cliente"
          onCancel={() => navigate("/clientes")}
          onSubmit={(payload) =>
            create.mutate(payload, {
              onSuccess: (customer) =>
                navigate(`/clientes/${customer.id}`, { replace: true }),
            })
          }
        />
      </section>
    </div>
  );
}
