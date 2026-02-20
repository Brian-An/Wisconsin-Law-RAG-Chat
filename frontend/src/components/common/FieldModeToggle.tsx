"use client";

import { Eye, EyeOff } from "lucide-react";
import { useUIStore } from "@/store/uiStore";

export function FieldModeToggle() {
  const fieldMode = useUIStore((s) => s.fieldMode);
  const toggleFieldMode = useUIStore((s) => s.toggleFieldMode);

  return (
    <button
      onClick={toggleFieldMode}
      className="flex items-center gap-2 rounded px-3 py-2 text-sm transition-all duration-300 hover:scale-[1.02]"
      style={{
        color: fieldMode ? "var(--color-success)" : "var(--text-secondary)",
        background: fieldMode ? "var(--border-light)" : "transparent",
        borderRadius: "var(--radius-button)",
      }}
      title={fieldMode ? "Disable Field Mode" : "Enable Field Mode"}
    >
      {fieldMode ? <Eye size={16} /> : <EyeOff size={16} />}
      <span style={{ fontSize: "var(--font-size-sm)" }}>Field Mode</span>
    </button>
  );
}
