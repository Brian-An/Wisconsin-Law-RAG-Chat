"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import type { Message } from "@/lib/types";
import { formatForReport } from "@/lib/utils";

interface ExportButtonProps {
  message: Message;
}

export function ExportButton({ message }: ExportButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = formatForReport(message);
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs transition-all duration-200 hover:scale-[1.02]"
      style={{
        color: copied ? "var(--color-success)" : "var(--text-secondary)",
        borderRadius: "var(--radius-button)",
        border: `1px solid ${copied ? "var(--color-success)" : "var(--border-light)"}`,
      }}
      title="Copy to Clipboard (Report Format)"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy for Report"}
    </button>
  );
}
