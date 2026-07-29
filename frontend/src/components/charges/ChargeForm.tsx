import { useState, type FormEvent } from "react";
import { userFacingError } from "../../api/errors";
import type { ChargePayload } from "../../api/types";
import { useCustomer, useCustomers } from "../../hooks/useCustomers";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";

function amountToDigits(amount: string | undefined) {
  if (!amount) return "";
  const normalized = amount.replace(",", ".");
  const [integer = "0", decimal = ""] = normalized.split(".");
  return `${integer.replace(/\D/g, "")}${decimal.padEnd(2, "0").slice(0, 2)}`
    .replace(/^0+/, "")
    .slice(0, 12);
}

function formatAmountInput(digits: string) {
  const cents = Number(digits || "0");
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(cents / 100);
}

function amountPayload(digits: string) {
  const padded = (digits || "0").padStart(3, "0");
  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function isoToDateInput(value: string | undefined) {
  if (!value) return "";
  const [year, month, day] = value.split("-");
  return day && month && year ? `${day}/${month}/${year}` : "";
}

function formatDateInput(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

function dateInputToIso(value: string) {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!match) return null;
  const [, day, month, year] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  if (
    date.getUTCFullYear() !== Number(year) ||
    date.getUTCMonth() !== Number(month) - 1 ||
    date.getUTCDate() !== Number(day)
  ) {
    return null;
  }
  return `${year}-${month}-${day}`;
}

export function ChargeForm({
  initialValue,
  loading,
  error,
  submitLabel,
  onCancel,
  onSubmit,
}: {
  initialValue?: ChargePayload;
  loading: boolean;
  error: unknown;
  submitLabel: string;
  onCancel: () => void;
  onSubmit: (payload: ChargePayload) => void;
}) {
  const [customerId, setCustomerId] = useState(initialValue?.customer_id ?? "");
  const [description, setDescription] = useState(initialValue?.description ?? "");
  const [amountDigits, setAmountDigits] = useState(
    amountToDigits(initialValue?.amount),
  );
  const [dueDate, setDueDate] = useState(
    isoToDateInput(initialValue?.due_date),
  );
  const [dateError, setDateError] = useState(false);
  const [reminderDays, setReminderDays] = useState(
    String(initialValue?.reminder_days_before ?? 3),
  );
  const [customerSearch, setCustomerSearch] = useState("");
  const customers = useCustomers({
    page: 1,
    pageSize: 25,
    active: true,
    search: customerSearch.trim() || undefined,
  });
  const selectedCustomer = useCustomer(customerId);
  const customerOptions = [...(customers.data?.items ?? [])];
  if (
    selectedCustomer.data &&
    !customerOptions.some((customer) => customer.id === selectedCustomer.data?.id)
  ) {
    customerOptions.unshift(selectedCustomer.data);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const dueDateIso = dateInputToIso(dueDate);
    if (!dueDateIso) {
      setDateError(true);
      return;
    }
    onSubmit({
      customer_id: customerId,
      description: description.trim(),
      amount: amountPayload(amountDigits),
      due_date: dueDateIso,
      reminder_days_before: Number(reminderDays),
    });
  }

  return (
    <form className="entity-form" onSubmit={submit}>
      <div className="form-grid">
        <label className="form-field form-field-wide">
          <span>Cliente</span>
          <input
            aria-label="Buscar cliente"
            onChange={(event) => setCustomerSearch(event.target.value)}
            placeholder="Digite o nome ou telefone para filtrar"
            type="search"
            value={customerSearch}
          />
          <select
            aria-label="Cliente"
            disabled={loading || customers.isLoading}
            onChange={(event) => setCustomerId(event.target.value)}
            required
            value={customerId}
          >
            <option value="">Selecione um cliente ativo</option>
            {customerOptions.map((customer) => (
              <option key={customer.id} value={customer.id}>{customer.name}</option>
            ))}
          </select>
          <small>A cobrança e as mensagens ficarão vinculadas a este cliente.</small>
        </label>
        <label className="form-field form-field-wide">
          <span>Descrição</span>
          <input
            aria-label="Descrição"
            lang="pt-BR"
            maxLength={255}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Ex.: Mensalidade de julho"
            required
            spellCheck={false}
            value={description}
          />
        </label>
        <label className="form-field">
          <span>Valor</span>
          <input
            aria-label="Valor"
            inputMode="numeric"
            onChange={(event) =>
              setAmountDigits(
                event.target.value
                  .replace(/\D/g, "")
                  .replace(/^0+/, "")
                  .slice(0, 12),
              )
            }
            required
            type="text"
            value={formatAmountInput(amountDigits)}
          />
          <small>Digite os centavos da direita para a esquerda.</small>
        </label>
        <label className="form-field">
          <span>Vencimento</span>
          <input
            aria-label="Vencimento"
            inputMode="numeric"
            maxLength={10}
            onChange={(event) => {
              setDueDate(formatDateInput(event.target.value));
              setDateError(false);
            }}
            pattern="\d{2}/\d{2}/\d{4}"
            placeholder="DD/MM/AAAA"
            required
            type="text"
            value={dueDate}
          />
          {dateError ? <small className="field-error">Informe uma data válida.</small> : null}
        </label>
        <label className="form-field">
          <span>Lembrar com antecedência</span>
          <input
            aria-label="Dias de antecedência"
            max="365"
            min="0"
            onChange={(event) => setReminderDays(event.target.value)}
            required
            type="number"
            value={reminderDays}
          />
          <small>Quantidade de dias antes do vencimento.</small>
        </label>
      </div>
      {error ? <div className="form-error" role="alert">{userFacingError(error)}</div> : null}
      <footer className="form-actions">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button loading={loading} type="submit" icon={<Icon name="check" />}>
          {submitLabel}
        </Button>
      </footer>
    </form>
  );
}
