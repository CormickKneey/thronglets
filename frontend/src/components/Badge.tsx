import type { ReactNode } from "react";
import "./Badge.css";

interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "primary" | "success" | "danger" | "warning";
  size?: "sm" | "md";
}

export function Badge({ children, variant = "default", size = "md" }: BadgeProps) {
  return (
    <span className={`brutal-badge brutal-badge--${variant} brutal-badge--${size}`}>
      {children}
    </span>
  );
}
