import { create } from "zustand";
import type { SourceInfo } from "@/lib/types";

interface UIState {
  sidebarOpen: boolean;
  sourcePanelOpen: boolean;
  activeSource: SourceInfo | null;
  activeQuery: string | null;
  fieldMode: boolean;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSourcePanelOpen: (open: boolean) => void;
  setActiveSource: (source: SourceInfo | null) => void;
  openSourcePanel: (source: SourceInfo, query?: string) => void;
  closeSourcePanel: () => void;
  toggleFieldMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  sourcePanelOpen: false,
  activeSource: null,
  activeQuery: null,
  fieldMode: false,

  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  setSourcePanelOpen: (open) => set({ sourcePanelOpen: open }),
  setActiveSource: (source) => set({ activeSource: source }),
  openSourcePanel: (source, query) =>
    set({ activeSource: source, activeQuery: query ?? null, sourcePanelOpen: true }),
  closeSourcePanel: () =>
    set({ sourcePanelOpen: false, activeSource: null, activeQuery: null }),

  toggleFieldMode: () => {
    set((state) => {
      const next = !state.fieldMode;
      if (typeof document !== "undefined") {
        document.documentElement.classList.toggle("field-mode", next);
      }
      return { fieldMode: next };
    });
  },
}));
