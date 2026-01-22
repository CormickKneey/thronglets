import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "default" | "primary" | "danger" | "outline";
  size?: "sm" | "md" | "lg";
}

export function Button({
  children,
  variant = "default",
  size = "md",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`brutal-btn brutal-btn--${variant} brutal-btn--${size} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
