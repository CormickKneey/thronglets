import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import "./Input.css";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = "", id, ...props }: InputProps) {
  const inputId = id || `input-${label?.toLowerCase().replace(/\s/g, "-")}`;

  return (
    <div className={`brutal-input-wrapper ${className}`}>
      {label && (
        <label htmlFor={inputId} className="brutal-input-label">
          {label}
        </label>
      )}
      <input id={inputId} className={`brutal-input ${error ? "brutal-input--error" : ""}`} {...props} />
      {error && <span className="brutal-input-error">{error}</span>}
    </div>
  );
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export function Textarea({ label, error, className = "", id, ...props }: TextareaProps) {
  const textareaId = id || `textarea-${label?.toLowerCase().replace(/\s/g, "-")}`;

  return (
    <div className={`brutal-input-wrapper ${className}`}>
      {label && (
        <label htmlFor={textareaId} className="brutal-input-label">
          {label}
        </label>
      )}
      <textarea
        id={textareaId}
        className={`brutal-textarea ${error ? "brutal-input--error" : ""}`}
        {...props}
      />
      {error && <span className="brutal-input-error">{error}</span>}
    </div>
  );
}
