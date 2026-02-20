"use client";

import { User, Bot } from "lucide-react";
import type { Message } from "@/lib/types";
import { CitationCard } from "./CitationCard";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { FlagBanner } from "./FlagBanner";
import { ExportButton } from "./ExportButton";

interface MessageBubbleProps {
  message: Message;
  query?: string;
}

export function MessageBubble({ message, query }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}
    >
      {/* Avatar */}
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
        style={{
          background: isUser ? "var(--accent-primary)" : "var(--border-medium)",
        }}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Message content */}
      <div
        className={`flex max-w-[80%] flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}
      >
        <div
          className="px-4 py-3"
          style={{
            background: isUser
              ? "var(--user-bubble-bg)"
              : "var(--assistant-bubble-bg)",
            color: isUser
              ? "var(--user-bubble-text)"
              : "var(--assistant-bubble-text)",
            borderRadius: "var(--radius-card)",
            fontSize: "var(--font-size-sm)",
            lineHeight: "1.6",
          }}
        >
          {/* Flags */}
          {!isUser && message.flags && <FlagBanner flags={message.flags} />}

          {/* Message text */}
          <div className="whitespace-pre-wrap">{message.content}</div>

          {/* Citations */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-3 flex flex-col gap-2">
              {message.sources.map((source, i) => (
                <CitationCard key={source.chunk_id || i} source={source} index={i} query={query} />
              ))}
            </div>
          )}
        </div>

        {/* Footer: timestamp, confidence, export */}
        <div
          className={`flex items-center gap-2 flex-wrap ${isUser ? "flex-row-reverse" : ""}`}
        >
          <span
            className="text-xs"
            style={{ color: "var(--text-secondary)" }}
          >
            {time}
          </span>

          {!isUser && message.confidence_score !== undefined && (
            <ConfidenceBadge score={message.confidence_score} />
          )}

          {!isUser && <ExportButton message={message} />}
        </div>

        {/* Disclaimer */}
        {!isUser && message.disclaimer && (
          <p
            className="text-xs italic mt-1"
            style={{
              color: "var(--text-secondary)",
              fontSize: "var(--font-size-sm)",
              opacity: 0.7,
            }}
          >
            {message.disclaimer}
          </p>
        )}
      </div>
    </div>
  );
}
