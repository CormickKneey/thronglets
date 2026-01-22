import type { ReactNode, CSSProperties } from "react";
import "./Card.css";

interface CardProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: () => void;
  variant?: "default" | "primary" | "outline";
}

export function Card({
  children,
  className = "",
  style,
  onClick,
  variant = "default",
}: CardProps) {
  return (
    <div
      className={`brutal-card brutal-card--${variant} ${className}`}
      style={style}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export function CardHeader({ children, className = "" }: CardHeaderProps) {
  return <div className={`brutal-card__header ${className}`}>{children}</div>;
}

interface CardBodyProps {
  children: ReactNode;
  className?: string;
}

export function CardBody({ children, className = "" }: CardBodyProps) {
  return <div className={`brutal-card__body ${className}`}>{children}</div>;
}

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

export function CardFooter({ children, className = "" }: CardFooterProps) {
  return <div className={`brutal-card__footer ${className}`}>{children}</div>;
}
