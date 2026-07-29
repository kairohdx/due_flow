import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({
  variant = "primary",
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  ...props
}, ref) {
  return (
    <button
      ref={ref}
      className={`button button-${variant} ${className}`.trim()}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <span className="button-spinner" aria-hidden="true" /> : icon}
      <span>{loading ? "Aguarde..." : children}</span>
    </button>
  );
});
