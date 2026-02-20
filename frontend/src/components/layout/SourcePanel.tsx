"use client";

import { X, FileText, BookOpen, Scale, Gavel } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { highlightKeywords } from "@/lib/highlight";
import { BottomSheet } from "./BottomSheet";

const TYPE_CONFIG: Record<
  string,
  { icon: React.ComponentType<{ size?: number }>; label: string; color: string }
> = {
  statute: { icon: Scale, label: "Statute", color: "var(--accent-primary)" },
  case_law: { icon: Gavel, label: "Case Law", color: "var(--color-warning)" },
  training: { icon: BookOpen, label: "Training", color: "var(--color-success)" },
};

const DEFAULT_TYPE = { icon: FileText, label: "Document", color: "var(--text-secondary)" };

function formatScore(score: number): string {
  const pct = Math.min(score / 0.033, 1.0) * 100;
  return `${pct.toFixed(0)}%`;
}

export function SourcePanel() {
  const activeSource = useUIStore((s) => s.activeSource);
  const activeQuery = useUIStore((s) => s.activeQuery);
  const sourcePanelOpen = useUIStore((s) => s.sourcePanelOpen);
  const closeSourcePanel = useUIStore((s) => s.closeSourcePanel);
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  if (!sourcePanelOpen || !activeSource) return null;

  const typeInfo = TYPE_CONFIG[activeSource.source_type] || DEFAULT_TYPE;
  const TypeIcon = typeInfo.icon;

  const content = (
    <div className="flex flex-col gap-4">
      {/* Type + score header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="flex h-7 w-7 items-center justify-center rounded"
            style={{ background: typeInfo.color }}
          >
            <TypeIcon size={16} />
          </div>
          <span
            className="text-sm font-semibold uppercase"
            style={{ color: typeInfo.color }}
          >
            {typeInfo.label}
          </span>
        </div>
        {activeSource.score > 0 && (
          <span
            className="px-2 py-0.5 text-xs font-semibold"
            style={{
              color: "var(--color-success-light)",
              borderRadius: "var(--radius-badge)",
              border: "1px solid var(--color-success)",
            }}
          >
            Match: {formatScore(activeSource.score)}
          </span>
        )}
      </div>

      {/* Title */}
      <div>
        <h4
          className="mb-1 text-xs font-semibold uppercase"
          style={{ color: "var(--text-secondary)" }}
        >
          Title
        </h4>
        <p
          className="text-sm font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          {activeSource.title}
        </p>
      </div>

      {/* Source file */}
      <div
        className="flex items-center gap-2 px-3 py-2 text-xs"
        style={{
          background: "var(--bg-secondary)",
          borderRadius: "var(--radius-button)",
          color: "var(--text-secondary)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <FileText size={14} />
        {activeSource.source_file
          ? activeSource.source_file.split("/").pop()
          : "Unknown file"}
      </div>

      {/* Context header / section */}
      {activeSource.context_header && (
        <div>
          <h4
            className="mb-1 text-xs font-semibold uppercase"
            style={{ color: "var(--text-secondary)" }}
          >
            Section
          </h4>
          <p
            className="text-sm"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {activeSource.context_header}
          </p>
        </div>
      )}

      {/* Statute numbers */}
      {activeSource.statute_numbers && (
        <div>
          <h4
            className="mb-1 text-xs font-semibold uppercase"
            style={{ color: "var(--text-secondary)" }}
          >
            Statutes
          </h4>
          <div className="flex flex-wrap gap-1">
            {activeSource.statute_numbers.split(",").map((s) => (
              <span
                key={s}
                className="px-2 py-0.5 text-xs"
                style={{
                  color: "var(--accent-primary)",
                  background: "var(--bg-secondary)",
                  borderRadius: "var(--radius-badge)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                § {s.trim()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Case citations */}
      {activeSource.case_citations && (
        <div>
          <h4
            className="mb-1 text-xs font-semibold uppercase"
            style={{ color: "var(--text-secondary)" }}
          >
            Case Citations
          </h4>
          <div className="flex flex-wrap gap-1">
            {activeSource.case_citations.split(",").map((c) => (
              <span
                key={c}
                className="px-2 py-0.5 text-xs"
                style={{
                  color: "var(--color-warning)",
                  background: "var(--bg-secondary)",
                  borderRadius: "var(--radius-badge)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {c.trim()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Document chunk */}
      {activeSource.document && (
        <div>
          <h4
            className="mb-1 text-xs font-semibold uppercase"
            style={{ color: "var(--text-secondary)" }}
          >
            Document Excerpt
          </h4>
          <p
            className="text-sm leading-relaxed whitespace-pre-wrap"
            style={{
              color: "var(--text-primary)",
              fontSize: "var(--font-size-sm)",
              background: "var(--bg-secondary)",
              padding: "12px",
              borderRadius: "var(--radius-button)",
              borderLeft: `3px solid ${typeInfo.color}`,
            }}
          >
            {highlightKeywords(activeSource.document, activeQuery)}
          </p>
        </div>
      )}

      {/* Chunk ID */}
      {activeSource.chunk_id && (
        <div
          className="text-xs"
          style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)", opacity: 0.6 }}
        >
          ID: {activeSource.chunk_id}
        </div>
      )}
    </div>
  );

  // Mobile: bottom sheet
  if (!isDesktop) {
    return (
      <BottomSheet
        isOpen={sourcePanelOpen}
        onClose={closeSourcePanel}
        title="Source Detail"
      >
        {content}
      </BottomSheet>
    );
  }

  // Desktop: side panel
  return (
    <aside
      className="flex h-full w-[360px] shrink-0 flex-col overflow-hidden border-l"
      style={{
        background: "var(--bg-primary)",
        borderColor: "var(--border-light)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--border-light)" }}
      >
        <div className="flex items-center gap-2">
          <BookOpen size={16} style={{ color: "var(--accent-primary)" }} />
          <h3
            className="text-sm font-semibold uppercase"
            style={{ color: "var(--text-primary)" }}
          >
            Source Detail
          </h3>
        </div>
        <button
          onClick={closeSourcePanel}
          className="rounded p-1 transition-all duration-200 hover:scale-[1.1]"
          style={{ color: "var(--text-secondary)" }}
        >
          <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {content}
      </div>
    </aside>
  );
}
