import type { ChargeStatus } from "../api/types";
import type { BadgeTone } from "../components/ui/StatusBadge";

export const chargeStatusMeta: Record<
  ChargeStatus,
  { label: string; tone: BadgeTone }
> = {
  pending: { label: "Pendente", tone: "warning" },
  paid: { label: "Paga", tone: "success" },
  canceled: { label: "Cancelada", tone: "neutral" },
};
