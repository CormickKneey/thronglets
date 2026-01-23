import { useState } from "react";
import { Button } from "./Button";
import { copyToClipboard } from "../utils/clipboard";

interface CopyButtonProps {
  text: string;
  size?: "sm" | "md" | "lg";
}

export function CopyButton({ text, size = "sm" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Button variant="outline" size={size} onClick={handleCopy}>
      {copied ? "Copied!" : "Copy"}
    </Button>
  );
}
