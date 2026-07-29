import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChargeForm } from "../components/charges/ChargeForm";
import { Icon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { useCreateCharge } from "../hooks/useCharges";

export function ChargeCreatePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const create = useCreateCharge();
  const customerId = params.get("customer_id") ?? "";

  return (
    <div className="page-stack entity-page">
      <Link className="back-link" to="/cobrancas">
        <Icon name="arrow-left" /> Voltar para cobranças
      </Link>
      <PageHeader
        eyebrow="Novo lançamento"
        title="Cadastrar cobrança"
        description="Informe o cliente, valor e vencimento que serão avaliados pela automação."
      />
      <section className="surface-card form-card">
        <div className="form-card-heading">
          <span className="form-heading-icon"><Icon name="credit-card" /></span>
          <div><h2>Informações da cobrança</h2><p>Você poderá editar enquanto ela estiver pendente.</p></div>
        </div>
        <ChargeForm
          initialValue={{
            customer_id: customerId,
            description: "",
            amount: "",
            due_date: "",
            reminder_days_before: 3,
          }}
          error={create.error}
          loading={create.isPending}
          submitLabel="Cadastrar cobrança"
          onCancel={() => navigate("/cobrancas")}
          onSubmit={(payload) =>
            create.mutate(payload, {
              onSuccess: (charge) =>
                navigate(`/cobrancas/${charge.id}`, { replace: true }),
            })
          }
        />
      </section>
    </div>
  );
}
