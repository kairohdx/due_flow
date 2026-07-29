import { useState, type FormEvent } from "react";
import { userFacingError } from "../../api/errors";
import type { CustomerPayload } from "../../api/types";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";

export function CustomerForm({
  initialValue,
  submitLabel,
  loading,
  error,
  onSubmit,
  onCancel,
}: {
  initialValue?: CustomerPayload;
  submitLabel: string;
  loading: boolean;
  error: unknown;
  onSubmit: (payload: CustomerPayload) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initialValue?.name ?? "");
  const [phone, setPhone] = useState(initialValue?.phone ?? "");
  const [active, setActive] = useState(initialValue?.active ?? true);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ name: name.trim(), phone: phone.trim(), active });
  }

  return (
    <form className="entity-form" onSubmit={submit}>
      <div className="form-grid">
        <label className="form-field form-field-wide">
          <span>Nome do cliente</span>
          <input
            aria-label="Nome do cliente"
            autoFocus
            maxLength={160}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ex.: Empresa Exemplo"
            required
            value={name}
          />
          <small>Use o nome pelo qual você identifica o cliente.</small>
        </label>
        <label className="form-field form-field-wide">
          <span>WhatsApp</span>
          <input
            aria-label="WhatsApp"
            autoComplete="tel"
            inputMode="tel"
            onChange={(event) => setPhone(event.target.value)}
            placeholder="+55 (11) 99999-0000"
            required
            value={phone}
          />
          <small>Inclua o código do país. O número será normalizado pela API.</small>
        </label>
        <label className="switch-field form-field-wide">
          <input
            aria-label="Cliente ativo"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
            type="checkbox"
          />
          <span className="switch-control" aria-hidden="true"><i /></span>
          <span>
            <strong>Cliente ativo</strong>
            <small>Clientes inativos não recebem novas notificações.</small>
          </span>
        </label>
      </div>
      {error ? (
        <div className="form-error" role="alert">{userFacingError(error)}</div>
      ) : null}
      <footer className="form-actions">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button
          loading={loading}
          type="submit"
          icon={<Icon name="check" />}
        >
          {submitLabel}
        </Button>
      </footer>
    </form>
  );
}
