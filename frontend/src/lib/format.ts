const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

const timeFormatter = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function formatDateTime(value: string | null): string {
  if (!value) return "Ainda não ocorreu";
  return dateTimeFormatter.format(new Date(value));
}

export function formatTime(value: string): string {
  return timeFormatter.format(new Date(value));
}

export function formatDuration(milliseconds: number | null): string {
  if (milliseconds == null) return "—";
  if (milliseconds < 1_000) return `${Math.round(milliseconds)} ms`;
  return `${(milliseconds / 1_000).toFixed(1)} s`;
}

export function formatInterval(seconds: number): string {
  if (seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes} ${minutes === 1 ? "minuto" : "minutos"}`;
  }
  return `${seconds} segundos`;
}

export function formatCurrency(value: string): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value));
}

export function formatDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return new Intl.DateTimeFormat("pt-BR").format(
    new Date(year, month - 1, day),
  );
}

export function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 13) {
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9)}`;
  }
  if (digits.length === 12) {
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 8)}-${digits.slice(8)}`;
  }
  return value;
}

export function maskBrazilianPhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  const nationalNumber = (
    digits.startsWith("55") ? digits.slice(2) : digits
  ).slice(0, 11);
  const areaCode = nationalNumber.slice(0, 2);
  const subscriber = nationalNumber.slice(2);

  let masked = "+55";
  if (areaCode) masked += ` (${areaCode}`;
  if (areaCode.length === 2) masked += ")";
  if (subscriber) {
    const prefixLength = subscriber.length > 8 ? 5 : 4;
    masked += ` ${subscriber.slice(0, prefixLength)}`;
    if (subscriber.length > prefixLength) {
      masked += `-${subscriber.slice(prefixLength)}`;
    }
  }
  return `${masked} `;
}

export function normalizeBrazilianPhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  const nationalNumber = digits.startsWith("55") ? digits.slice(2) : digits;
  return `+55${nationalNumber}`;
}
