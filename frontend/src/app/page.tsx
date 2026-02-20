"use client";

import { useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ChatStream } from "@/components/chat/ChatStream";
import { ChatInput } from "@/components/input/ChatInput";
import { QuickActionGrid } from "@/components/input/QuickActionGrid";
import { ExportChatButton } from "@/components/chat/ExportChatButton";
import { useChat } from "@/hooks/useChat";
import { useChatStore } from "@/store/chatStore";

export default function Home() {
  const { sendMessage, messages, isLoading } = useChat();
  const loadFromStorage = useChatStore((s) => s.loadFromStorage);
  const conversations = useChatStore((s) => s.conversations);
  const activeConversationId = useChatStore((s) => s.activeConversationId);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId,
  );

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return (
    <AppShell>
      <div className="flex h-full flex-col">
        {/* Header bar with title + export controls */}
        <div
          className="flex shrink-0 items-center justify-between px-4 py-2"
          style={{ borderBottom: "1px solid var(--border-light)" }}
        >
          <span
            className="text-sm font-semibold truncate"
            style={{ color: "var(--text-primary)" }}
          >
            {activeConversation ? activeConversation.title : "New Conversation"}
          </span>
          <ExportChatButton conversation={activeConversation} />
        </div>

        {messages.length === 0 && !isLoading ? (
          <EmptyState />
        ) : (
          <ChatStream messages={messages} isLoading={isLoading} />
        )}
        <QuickActionGrid onAction={sendMessage} />
        <ChatInput onSend={sendMessage} isLoading={isLoading} />
      </div>
    </AppShell>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <h1
        className="mb-2 text-2xl font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        Wisconsin Law Enforcement RAG
      </h1>
      <p
        className="text-sm text-center max-w-md"
        style={{ color: "var(--text-secondary)" }}
      >
        Ask questions about Wisconsin statutes, case law, and department
        policies. Use the quick actions below or type your own question.
      </p>
    </div>
  );
}
