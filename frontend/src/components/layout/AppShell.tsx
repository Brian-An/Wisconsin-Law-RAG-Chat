"use client";

import { Sidebar } from "./Sidebar";
import { SourcePanel } from "./SourcePanel";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: "var(--bg-primary)" }}
    >
      <Sidebar />
      <main className="flex flex-1 flex-col overflow-hidden">
        {children}
      </main>
      <SourcePanel />
    </div>
  );
}
