import { EmptyState } from "../components/feedback/EmptyState";
import { Button } from "../components/ui/Button";
import { Icon, type IconName } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";

const content: Record<
  string,
  { eyebrow: string; title: string; description: string; icon: IconName }
> = {
  dashboard: {
    eyebrow: "Operação em tempo real",
    title: "Olá, vamos colocar suas cobranças em movimento.",
    description:
      "O resumo operacional com métricas e polling será conectado na Etapa 7.4.",
    icon: "dashboard",
  },
  customers: {
    eyebrow: "Base de contatos",
    title: "Clientes",
    description:
      "Cadastros, detalhes e cobranças relacionadas chegam na Etapa 7.5.",
    icon: "users",
  },
  charges: {
    eyebrow: "Gestão financeira",
    title: "Cobranças",
    description:
      "Listagem, filtros e ações de cobrança serão conectados na Etapa 7.6.",
    icon: "credit-card",
  },
  jobs: {
    eyebrow: "Automação auditável",
    title: "Fila de jobs",
    description:
      "Acompanhamento ao vivo e inspeção do turno chegam na Etapa 7.7.",
    icon: "activity",
  },
  notifications: {
    eyebrow: "Histórico de envios",
    title: "Notificações",
    description:
      "Tentativas, mensagens e traces serão conectados na Etapa 7.8.",
    icon: "bell",
  },
  settings: {
    eyebrow: "Preferências",
    title: "Configurações",
    description:
      "Os controles essenciais aparecerão aqui conforme as telas forem conectadas.",
    icon: "settings",
  },
};

export function FoundationPage({ type }: { type: keyof typeof content }) {
  const page = content[type];
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={page.eyebrow}
        title={page.title}
        description={page.description}
        actions={
          type === "dashboard" ? (
            <StatusBadge tone="info">Fundação pronta</StatusBadge>
          ) : null
        }
      />
      <section className="foundation-grid">
        <div className="surface-card foundation-main">
          <EmptyState
            icon={page.icon}
            title="Estrutura preparada"
            description="Esta rota já está protegida, responsiva e pronta para consumir os contratos da API."
            action={
              <Button variant="secondary" icon={<Icon name="sparkles" />}>
                Próxima etapa
              </Button>
            }
          />
        </div>
        <aside className="surface-card foundation-aside">
          <span className="eyebrow">Nesta fundação</span>
          <ul className="check-list">
            <li><i />Sessão restaurada por refresh token</li>
            <li><i />Rotas privadas protegidas</li>
            <li><i />Cache remoto com TanStack Query</li>
            <li><i />Componentes e tokens visuais</li>
          </ul>
        </aside>
      </section>
    </div>
  );
}
