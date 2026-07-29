import type { ReactNode } from "react";

export interface TableColumn<Row> {
  key: string;
  label: string;
  render: (row: Row) => ReactNode;
  align?: "left" | "right";
}

export function DataTable<Row>({
  columns,
  rows,
  rowKey,
}: {
  columns: TableColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
}) {
  return (
    <div className="table-frame">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={`align-${column.align ?? "left"}`}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={column.key} className={`align-${column.align ?? "left"}`}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
