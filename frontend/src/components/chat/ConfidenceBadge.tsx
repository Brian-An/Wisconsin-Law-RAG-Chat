"use client";

import { AlertTriangle } from "lucide-react";
import { getConfidenceLevel } from "@/lib/utils";

interface ConfidenceBadgeProps {
  score: number;
}

const LEVEL_STYLES = {
  high: { color: "var(--color-success-light)", label: "High Confidence" },
  medium: { color: "var(--color-warning-light)", label: "Medium Confidence" },
  low: { color: "var(--color-error)", label: "Low Confidence — Verify" },
} as const;

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const level = getConfidenceLevel(score);
  const style = LEVEL_STYLES[level];

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold uppercase"
      style={{
        color: style.color,
        borderRadius: "var(--radius-badge)",
        border: `1px solid ${style.color}`,
      }}
    >
      {level === "low" && <AlertTriangle size={12} />}
      {style.label}
      <span className="opacity-70">({(score * 100).toFixed(0)}%)</span>
    </span>
  );
}
