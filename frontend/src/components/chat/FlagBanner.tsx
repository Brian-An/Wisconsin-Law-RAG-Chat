"use client";

import { AlertTriangle, Clock, MapPin, ShieldAlert } from "lucide-react";
import type { ResponseFlags } from "@/lib/types";

interface FlagBannerProps {
  flags: ResponseFlags;
}

const FLAG_CONFIG = [
  {
    key: "USE_OF_FORCE_CAUTION" as const,
    icon: ShieldAlert,
    text: "Use of force topic — always consult department-specific policies.",
    color: "var(--color-error)",
  },
  {
    key: "LOW_CONFIDENCE" as const,
    icon: AlertTriangle,
    text: "Low confidence — verify this information with authoritative sources.",
    color: "var(--color-warning)",
  },
  {
    key: "OUTDATED_POSSIBLE" as const,
    icon: Clock,
    text: "Source may be outdated — check against current statutes.",
    color: "var(--color-warning-light)",
  },
  {
    key: "JURISDICTION_NOTE" as const,
    icon: MapPin,
    text: "Jurisdiction-specific — other jurisdictions may differ.",
    color: "var(--text-secondary)",
  },
];

export function FlagBanner({ flags }: FlagBannerProps) {
  const activeFlags = FLAG_CONFIG.filter((f) => flags[f.key]);

  if (activeFlags.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5">
      {activeFlags.map((flag) => {
        const Icon = flag.icon;
        return (
          <div
            key={flag.key}
            className="flex items-center gap-2 px-3 py-1.5 text-xs"
            style={{
              color: flag.color,
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-button)",
              borderLeft: `3px solid ${flag.color}`,
            }}
          >
            <Icon size={14} className="shrink-0" />
            <span>{flag.text}</span>
          </div>
        );
      })}
    </div>
  );
}
