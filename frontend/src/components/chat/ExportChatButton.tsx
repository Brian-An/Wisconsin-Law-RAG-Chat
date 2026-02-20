"use client";

import { useState } from "react";
import { ClipboardCopy, Check, Download } from "lucide-react";
import type { Conversation } from "@/lib/types";
import { formatConversationForReport } from "@/lib/utils";

interface ExportChatButtonProps {
  conversation: Conversation | undefined;
}

export function ExportChatButton({ conversation }: ExportChatButtonProps) {
  const [copied, setCopied] = useState(false);

  if (!conversation || conversation.messages.length === 0) return null;

  const getReportText = () => formatConversationForReport(conversation);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(getReportText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownload = () => {
    const text = getReportText();
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const date = new Date().toISOString().split("T")[0];
    const slug = conversation.title
      .replace(/[^a-zA-Z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .substring(0, 40)
      .toLowerCase();
    a.download = `report_${slug}_${date}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={handleCopy}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all duration-200 hover:scale-[1.02]"
        style={{
          background: copied ? "var(--color-success)" : "var(--bg-card)",
          border: `1px solid ${copied ? "var(--color-success)" : "var(--border-light)"}`,
          borderRadius: "var(--radius-badge)",
          color: copied ? "#fff" : "var(--text-secondary)",
          whiteSpace: "nowrap",
        }}
        title="Copy entire chat history to clipboard in report format"
      >
        {copied ? <Check size={14} /> : <ClipboardCopy size={14} />}
        {copied ? "Copied!" : "Copy Chat"}
      </button>
      <button
        onClick={handleDownload}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all duration-200 hover:scale-[1.02]"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-light)",
          borderRadius: "var(--radius-badge)",
          color: "var(--text-secondary)",
          whiteSpace: "nowrap",
        }}
        title="Download chat history as a text file for report writing"
      >
        <Download size={14} />
        Export .txt
      </button>
    </div>
  );
}
