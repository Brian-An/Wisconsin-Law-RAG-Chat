"use client";

import { Scale, Gavel, BookOpen, FileText } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { highlightKeywords } from "@/lib/highlight";
import type { SourceInfo } from "@/lib/types";

interface CitationCardProps {
  source: SourceInfo;
  index: number;
  query?: string;
}

const TYPE_CONFIG: Record<
  string,
  { icon: React.ComponentType<{ size?: number }>; label: string; color: string }
> = {
  statute: { icon: Scale, label: "Statute", color: "var(--accent-primary)" },
  case_law: { icon: Gavel, label: "Case Law", color: "var(--color-warning)" },
  training: {
    icon: BookOpen,
    label: "Training",
    color: "var(--color-success)",
  },
};

const DEFAULT_TYPE = {
  icon: FileText,
  label: "Document",
  color: "var(--text-secondary)",
};

function formatScore(score: number): string {
  // RRF scores are small (max ~0.033), normalize to percentage for display
  const pct = Math.min(score / 0.033, 1.0) * 100;
  return `${pct.toFixed(0)}%`;
}

export function CitationCard({ source, index, query }: CitationCardProps) {
  const openSourcePanel = useUIStore((s) => s.openSourcePanel);
  const typeInfo = TYPE_CONFIG[source.source_type] || DEFAULT_TYPE;
  const Icon = typeInfo.icon;

  const preview = source.document
    ? source.document.length > 150
      ? source.document.substring(0, 150) + "..."
      : source.document
    : null;

  return (
    <button
      onClick={() => openSourcePanel(source, query)}
      className="flex w-full flex-col gap-2 p-3 text-left transition-all duration-300 hover:-translate-y-0.5"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-light)",
        borderRadius: "var(--radius-card)",
      }}
    >
      {/* Top row: type badge + score */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div
            className="flex h-6 w-6 items-center justify-center rounded"
            style={{ background: typeInfo.color, opacity: 0.9 }}
          >
            <Icon size={14} />
          </div>
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: typeInfo.color }}
          >
            {typeInfo.label}
          </span>
          <span
            className="text-xs opacity-50"
            style={{
              color: "var(--text-secondary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            #{index + 1}
          </span>
        </div>
        {source.score > 0 && (
          <span
            className="px-2 py-0.5 text-xs font-semibold"
            style={{
              color: "var(--color-success-light)",
              borderRadius: "var(--radius-badge)",
              border: "1px solid var(--color-success)",
            }}
          >
            {formatScore(source.score)}
          </span>
        )}
      </div>

      {/* Title */}
      <p
        className="text-sm font-medium leading-snug"
        style={{ color: "var(--text-primary)" }}
      >
        {source.title}
        {source.context_header && (
          <span
            className="ml-1.5 text-xs font-normal"
            style={{ color: "var(--text-secondary)" }}
          >
            — {source.context_header}
          </span>
        )}
      </p>

      {/* Chunk preview */}
      {preview && (
        <p
          className="text-xs leading-relaxed line-clamp-3"
          style={{
            color: "var(--text-secondary)",
            fontSize: "var(--font-size-sm)",
            opacity: 0.8,
          }}
        >
          {highlightKeywords(preview, query)}
        </p>
      )}

      {/* Bottom row: source file + metadata */}
      <div className="flex items-center gap-2 flex-wrap">
        {source.source_file && (
          <span
            className="text-xs"
            style={{
              color: "var(--text-secondary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {source.source_file.split("/").pop()}
          </span>
        )}
        {source.statute_numbers && (
          <span
            className="px-1.5 py-0.5 text-xs"
            style={{
              color: "var(--accent-primary)",
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-badge)",
              fontFamily: "var(--font-mono)",
            }}
          >
            § {source.statute_numbers}
          </span>
        )}
        {source.case_citations && (
          <span
            className="px-1.5 py-0.5 text-xs"
            style={{
              color: "var(--color-warning)",
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-badge)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {source.case_citations}
          </span>
        )}
      </div>
    </button>
  );
}
