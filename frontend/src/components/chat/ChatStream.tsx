"use client";

import type { Message } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { SkeletonLoader } from "@/components/common/SkeletonLoader";
import { useScrollToBottom } from "@/hooks/useScrollToBottom";

interface ChatStreamProps {
  messages: Message[];
  isLoading: boolean;
}

export function ChatStream({ messages, isLoading }: ChatStreamProps) {
  const scrollRef = useScrollToBottom<HTMLDivElement>([messages.length, isLoading]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {messages.map((msg, i) => {
          const query =
            msg.role === "assistant"
              ? messages
                  .slice(0, i)
                  .reverse()
                  .find((m) => m.role === "user")?.content
              : undefined;
          return (
            <MessageBubble key={msg.id} message={msg} query={query} />
          );
        })}
        {isLoading && (
          <div className="flex gap-3">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
              style={{ background: "var(--border-medium)" }}
            >
              <div className="skeleton h-4 w-4 rounded-full" />
            </div>
            <div
              className="flex-1 max-w-[80%]"
              style={{
                background: "var(--assistant-bubble-bg)",
                borderRadius: "var(--radius-card)",
              }}
            >
              <SkeletonLoader />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
