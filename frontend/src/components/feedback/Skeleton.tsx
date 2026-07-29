export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-stack" aria-label="Carregando">
      {Array.from({ length: lines }, (_, index) => (
        <span
          className="skeleton-line"
          key={index}
          style={{ width: `${100 - (index % 3) * 12}%` }}
        />
      ))}
    </div>
  );
}
