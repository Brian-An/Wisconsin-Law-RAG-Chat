"use client";

import { Plus, MessageSquare, Trash2, Menu, X } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { useUIStore } from "@/store/uiStore";
import { useHealth } from "@/hooks/useHealth";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { FieldModeToggle } from "@/components/common/FieldModeToggle";
import { groupConversations } from "@/lib/utils";

export function Sidebar() {
  const conversations = useChatStore((s) => s.conversations);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const createConversation = useChatStore((s) => s.createConversation);
  const setActiveConversation = useChatStore((s) => s.setActiveConversation);
  const deleteConversation = useChatStore((s) => s.deleteConversation);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const health = useHealth();
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  const grouped = groupConversations(conversations);

  const handleNewChat = () => {
    createConversation();
    if (!isDesktop) setSidebarOpen(false);
  };

  const handleSelect = (id: string) => {
    setActiveConversation(id);
    if (!isDesktop) setSidebarOpen(false);
  };

  // Mobile: overlay sidebar
  if (!isDesktop) {
    return (
      <>
        {/* Hamburger toggle */}
        <button
          onClick={() => setSidebarOpen(true)}
          className="fixed left-3 top-3 z-40 rounded p-2 transition-all duration-200"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-light)",
            borderRadius: "var(--radius-button)",
            color: "var(--text-primary)",
          }}
        >
          <Menu size={20} />
        </button>

        {/* Overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-50">
            <div
              className="absolute inset-0 animate-fade-in"
              style={{ background: "rgba(0, 0, 0, 0.5)" }}
              onClick={() => setSidebarOpen(false)}
            />
            <aside
              className="absolute left-0 top-0 bottom-0 flex w-72 flex-col overflow-hidden"
              style={{
                background: "var(--bg-secondary)",
                borderRight: "1px solid var(--border-light)",
                animation: "slideRight 0.3s ease-out forwards",
              }}
            >
              <SidebarContent
                onNewChat={handleNewChat}
                onClose={() => setSidebarOpen(false)}
                health={health}
                grouped={grouped}
                activeConversationId={activeConversationId}
                onSelect={handleSelect}
                onDelete={deleteConversation}
              />
            </aside>
          </div>
        )}
      </>
    );
  }

  // Desktop: fixed sidebar
  if (!sidebarOpen) {
    return (
      <aside
        className="flex h-full w-16 shrink-0 flex-col items-center border-r py-3"
        style={{
          background: "var(--bg-secondary)",
          borderColor: "var(--border-light)",
        }}
      >
        <button
          onClick={() => setSidebarOpen(true)}
          className="rounded p-2 transition-all duration-200"
          style={{ color: "var(--text-secondary)" }}
        >
          <Menu size={20} />
        </button>
        <button
          onClick={handleNewChat}
          className="mt-2 rounded p-2 transition-all duration-200"
          style={{ color: "var(--accent-primary)" }}
          title="New chat"
        >
          <Plus size={20} />
        </button>
      </aside>
    );
  }

  return (
    <aside
      className="flex h-full w-[280px] shrink-0 flex-col overflow-hidden border-r"
      style={{
        background: "var(--bg-secondary)",
        borderColor: "var(--border-light)",
      }}
    >
      <SidebarContent
        onNewChat={handleNewChat}
        onClose={() => setSidebarOpen(false)}
        health={health}
        grouped={grouped}
        activeConversationId={activeConversationId}
        onSelect={handleSelect}
        onDelete={deleteConversation}
      />
    </aside>
  );
}

function SidebarContent({
  onNewChat,
  onClose,
  health,
  grouped,
  activeConversationId,
  onSelect,
  onDelete,
}: {
  onNewChat: () => void;
  onClose: () => void;
  health: ReturnType<typeof useHealth>;
  grouped: ReturnType<typeof groupConversations>;
  activeConversationId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--border-light)" }}
      >
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-semibold uppercase"
            style={{ color: "var(--text-primary)" }}
          >
            Chats
          </span>
          {health && (
            <span
              className="h-2 w-2 rounded-full"
              style={{
                background:
                  health.status === "ok"
                    ? "var(--color-success)"
                    : "var(--color-error)",
              }}
              title={`Backend: ${health.status} (${health.collection_count} docs)`}
            />
          )}
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 transition-all duration-200"
          style={{ color: "var(--text-secondary)" }}
        >
          <X size={18} />
        </button>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center justify-center gap-2 px-3 py-2 text-sm font-medium transition-all duration-300 hover:scale-[1.02]"
          style={{
            background: "var(--accent-primary)",
            color: "#ffffff",
            borderRadius: "var(--radius-button)",
          }}
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-1 py-2 field-mode-hide">
        {grouped.today.length === 0 &&
          grouped.yesterday.length === 0 &&
          grouped.older.length === 0 && (
            <p
              className="px-3 py-4 text-center text-xs"
              style={{ color: "var(--text-secondary)" }}
            >
              No conversations yet
            </p>
          )}
        <ConversationGroup
          label="Today"
          items={grouped.today}
          activeId={activeConversationId}
          onSelect={onSelect}
          onDelete={onDelete}
        />
        <ConversationGroup
          label="Yesterday"
          items={grouped.yesterday}
          activeId={activeConversationId}
          onSelect={onSelect}
          onDelete={onDelete}
        />
        <ConversationGroup
          label="Older"
          items={grouped.older}
          activeId={activeConversationId}
          onSelect={onSelect}
          onDelete={onDelete}
        />
      </div>

      {/* Field mode toggle */}
      <div
        className="border-t px-3 py-3"
        style={{ borderColor: "var(--border-light)" }}
      >
        <FieldModeToggle />
      </div>
    </>
  );
}

function ConversationGroup({
  label,
  items,
  activeId,
  onSelect,
  onDelete,
}: {
  label: string;
  items: { id: string; title: string }[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mb-4">
      <h4
        className="mb-2 px-3 text-xs font-semibold uppercase"
        style={{ color: "var(--text-secondary)" }}
      >
        {label}
      </h4>
      <div className="flex flex-col gap-0.5">
        {items.map((conv) => (
          <div
            key={conv.id}
            className="group flex items-center gap-2 rounded px-3 py-2 cursor-pointer transition-all duration-200"
            style={{
              background:
                conv.id === activeId ? "var(--border-light)" : "transparent",
              borderRadius: "var(--radius-button)",
            }}
            onClick={() => onSelect(conv.id)}
          >
            <MessageSquare
              size={14}
              className="shrink-0"
              style={{ color: "var(--text-secondary)" }}
            />
            <span
              className="flex-1 truncate text-sm"
              style={{
                color:
                  conv.id === activeId
                    ? "var(--text-primary)"
                    : "var(--text-secondary)",
              }}
            >
              {conv.title}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
              className="hidden rounded p-1 transition-all duration-200 hover:scale-[1.1] group-hover:block"
              style={{ color: "var(--color-error)" }}
              title="Delete conversation"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
