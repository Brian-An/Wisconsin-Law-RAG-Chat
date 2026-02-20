"use client";

import {
  Scale,
  Car,
  Search,
  Shield,
  CarFront,
  ShieldAlert,
  FileSearch,
  Siren,
} from "lucide-react";
import { QUICK_ACTIONS } from "@/lib/constants";

interface QuickActionGridProps {
  onAction: (query: string) => void;
}

const ICON_MAP: Record<string, React.ComponentType<{ size?: number }>> = {
  Scale,
  Car,
  Search,
  Shield,
  CarFront,
  ShieldAlert,
  FileSearch,
  Siren,
};

export function QuickActionGrid({ onAction }: QuickActionGridProps) {
  return (
    <div
      className="flex items-center gap-2 overflow-x-auto px-4 py-2 no-scrollbar"
      style={{ borderTop: "1px solid var(--border-light)" }}
    >
      {QUICK_ACTIONS.map((action) => {
        const Icon = ICON_MAP[action.icon];
        return (
          <button
            key={action.id}
            onClick={() => onAction(action.query)}
            className="flex shrink-0 items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all duration-200 hover:scale-[1.02]"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-light)",
              borderRadius: "var(--radius-badge)",
              color: "var(--text-secondary)",
              whiteSpace: "nowrap",
            }}
          >
            {Icon && <Icon size={14} />}
            {action.label}
          </button>
        );
      })}
    </div>
  );
}
