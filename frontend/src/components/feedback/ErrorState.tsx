import { userFacingError } from "../../api/errors";
import { Button } from "../ui/Button";

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <strong>Não foi possível carregar esta área</strong>
      <p>{userFacingError(error)}</p>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          Tentar novamente
        </Button>
      ) : null}
    </div>
  );
}
