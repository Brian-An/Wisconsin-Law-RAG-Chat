"use client";

import { useState, useRef, useCallback } from "react";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (query: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isLoading, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  return (
    <div
      className="border-t px-4 py-3"
      style={{ borderColor: "var(--border-light)" }}
    >
      <div
        className="mx-auto flex max-w-3xl items-end gap-2"
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            handleInput();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask about Wisconsin statutes, case law, or policies..."
          rows={1}
          disabled={isLoading}
          className="flex-1 resize-none px-4 py-3 text-sm outline-none transition-all duration-200 placeholder:opacity-50"
          style={{
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-input)",
            border: "1px solid var(--border-light)",
            minHeight: "48px",
            fontSize: "var(--font-size-sm)",
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading}
          className="flex items-center justify-center transition-all duration-300 hover:scale-[1.02] disabled:opacity-40 disabled:hover:scale-100"
          style={{
            background: "var(--accent-primary)",
            color: "#ffffff",
            borderRadius: "var(--radius-button)",
            minHeight: "48px",
            minWidth: "48px",
          }}
        >
          {isLoading ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Send size={20} />
          )}
        </button>
      </div>
    </div>
  );
}
