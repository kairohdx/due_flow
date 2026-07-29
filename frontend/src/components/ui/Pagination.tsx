import { Button } from "./Button";
import { Icon } from "./Icon";

export function Pagination({
  page,
  pages,
  total,
  onPageChange,
}: {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const safePages = Math.max(pages, 1);
  return (
    <nav className="pagination" aria-label="Paginação">
      <span className="pagination-total">
        {total} {total === 1 ? "item" : "itens"}
      </span>
      <div className="pagination-controls">
        <Button
          variant="secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          icon={<Icon name="arrow-left" />}
          aria-label="Página anterior"
        >
          Anterior
        </Button>
        <span className="pagination-page">
          Página <strong>{page}</strong> de {safePages}
        </span>
        <Button
          variant="secondary"
          disabled={pages === 0 || page >= pages}
          onClick={() => onPageChange(page + 1)}
          icon={<Icon name="arrow-right" />}
          aria-label="Próxima página"
        >
          Próxima
        </Button>
      </div>
    </nav>
  );
}
