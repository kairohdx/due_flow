import type {
  NotificationProvider,
  NotificationStatus,
  NotificationType,
} from "../api/types";
import type { BadgeTone } from "../components/ui/StatusBadge";

export const notificationStatusMeta: Record<
  NotificationStatus,
  { label: string; tone: BadgeTone }
> = {
  pending: { label: "Aguardando", tone: "warning" },
  sent: { label: "Enviada", tone: "success" },
  simulated: { label: "Simulada", tone: "info" },
  failed: { label: "Falhou", tone: "danger" },
};

export const notificationTypeLabel: Record<NotificationType, string> = {
  upcoming: "Lembrete antecipado",
  due_today: "Vencimento hoje",
  overdue: "Cobrança vencida",
};

export const notificationProviderLabel: Record<NotificationProvider, string> = {
  fake: "Simulador",
  meta: "WhatsApp Meta",
};
