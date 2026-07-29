import type {
  NotificationAttempt,
  NotificationProvider,
  NotificationSubmissionStatus,
  NotificationType,
} from "../api/types";
import type { BadgeTone } from "../components/ui/StatusBadge";

export const notificationStatusMeta: Record<
  NotificationSubmissionStatus,
  { label: string; tone: BadgeTone }
> = {
  pending: { label: "Aguardando", tone: "warning" },
  succeeded: { label: "Envio aceito", tone: "success" },
  simulated: { label: "Simulada", tone: "info" },
  failed: { label: "Falhou", tone: "danger" },
  unknown: { label: "Resultado incerto", tone: "warning" },
};

export function notificationSubmissionMeta(
  attempt: NotificationAttempt,
): { label: string; tone: BadgeTone } {
  return notificationStatusMeta[attempt.submission_status];
}

export function notificationDeliveryMeta(
  attempt: NotificationAttempt,
): { label: string; tone: BadgeTone } {
  switch (attempt.delivery_status) {
    case "not_started":
      return { label: "Não iniciada", tone: "neutral" };
    case "pending":
      return { label: "Aguardando entrega", tone: "warning" };
    case "sent":
      return { label: "Encaminhada", tone: "info" };
    case "delivered":
      return { label: "Entregue", tone: "success" };
    case "read":
      return { label: "Lida", tone: "success" };
    case "failed":
      return { label: "Falha na entrega", tone: "danger" };
    default:
      return { label: "Não iniciada", tone: "neutral" };
  }
}

export function notificationResultMeta(
  attempt: NotificationAttempt,
): { label: string; tone: BadgeTone } {
  if (attempt.delivery_status !== "not_started") {
    return notificationDeliveryMeta(attempt);
  }
  return notificationSubmissionMeta(attempt);
}

export const notificationTypeLabel: Record<NotificationType, string> = {
  upcoming: "Lembrete antecipado",
  due_today: "Vencimento hoje",
  overdue: "Cobrança vencida",
};

export const notificationProviderLabel: Record<NotificationProvider, string> = {
  fake: "Simulador",
  meta: "WhatsApp Meta",
};
