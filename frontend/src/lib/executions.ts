import type { JobOrigin, JobStatus, JobType } from "../api/types";
import type { BadgeTone } from "../components/ui/StatusBadge";

export const executionStatusMeta: Record<
  JobStatus,
  { label: string; tone: BadgeTone }
> = {
  queued: { label: "Aguardando", tone: "warning" },
  processing: { label: "Em execução", tone: "info" },
  completed: { label: "Concluída", tone: "success" },
  failed: { label: "Falhou", tone: "danger" },
};

export const executionOriginLabel: Record<JobOrigin, string> = {
  manual: "Manual",
  automatic: "Automática",
};

export const executionTypeLabel: Record<JobType, string> = {
  process_charge: "Cobrança individual",
  process_due_charges: "Verificação geral",
  retry_notification: "Retentativa de mensagem",
};
