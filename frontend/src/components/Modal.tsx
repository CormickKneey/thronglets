import type { ReactNode } from "react";
import { useEffect } from "react";
import { Button } from "./Button";
import "./Modal.css";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({ isOpen, onClose, title, children, footer }: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="brutal-modal-overlay" onClick={onClose}>
      <div
        className="brutal-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="brutal-modal__header">
          <h3 id="modal-title">{title}</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            aria-label="Close modal"
          >
            X
          </Button>
        </div>
        <div className="brutal-modal__body">{children}</div>
        {footer && <div className="brutal-modal__footer">{footer}</div>}
      </div>
    </div>
  );
}
