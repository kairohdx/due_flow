import type { ChargeStatus } from "../api/types";
import type { BadgeTone } from "../components/ui/StatusBadge";

export const chargeStatusMeta: Record<
  ChargeStatus,
  { label: string; tone: BadgeTone }
> = {
  pending: { label: "Em aberto", tone: "warning" },
  paid: { label: "Paga", tone: "success" },
  canceled: { label: "Cancelada", tone: "neutral" },
};

export function chargeDeadlineState(
  status: ChargeStatus,
  dueDate: string,
  reminderDaysBefore = 0,
): "overdue" | "today" | "upcoming" | "normal" {
  if (status !== "pending") return "normal";
  const now = new Date();
  const today = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
  if (dueDate < today) return "overdue";
  if (dueDate === today) return "today";
  const reminderLimit = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + reminderDaysBefore,
  );
  const limit = [
    reminderLimit.getFullYear(),
    String(reminderLimit.getMonth() + 1).padStart(2, "0"),
    String(reminderLimit.getDate()).padStart(2, "0"),
  ].join("-");
  if (reminderDaysBefore > 0 && dueDate <= limit) return "upcoming";
  return "normal";
}
