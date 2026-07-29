import type { ReactNode } from "react";
import { Icon, type IconName } from "../ui/Icon";

export function EmptyState({
  icon = "sparkles",
  title,
  description,
  action,
}: {
  icon?: IconName;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><Icon name={icon} /></span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </div>
  );
}
