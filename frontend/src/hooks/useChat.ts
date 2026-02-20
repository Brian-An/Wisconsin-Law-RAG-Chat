"use client";

import { useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { api } from "@/lib/api";
import { useChatStore } from "@/store/chatStore";
import type { Message } from "@/lib/types";

export function useChat() {
  const conversations = useChatStore((s) => s.conversations);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const isLoading = useChatStore((s) => s.isLoading);
  const error = useChatStore((s) => s.error);
  const createConversation = useChatStore((s) => s.createConversation);
  const addMessage = useChatStore((s) => s.addMessage);
  const setLoading = useChatStore((s) => s.setLoading);
  const setError = useChatStore((s) => s.setError);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );

  const sendMessage = useCallback(
    async (query: string) => {
      let convId = activeConversationId;
      if (!convId) {
        convId = createConversation();
      }

      const conv = useChatStore
        .getState()
        .conversations.find((c) => c.id === convId)!;

      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content: query,
        timestamp: Date.now(),
      };
      addMessage(convId, userMessage);

      setLoading(true);
      setError(null);

      try {
        const response = await api.chat({
          query,
          session_id: conv.session_id,
        });

        const assistantMessage: Message = {
          id: uuidv4(),
          role: "assistant",
          content: response.answer,
          timestamp: Date.now(),
          sources: response.sources,
          confidence_score: response.confidence_score,
          flags: response.flags,
          disclaimer: response.disclaimer,
        };
        addMessage(convId, assistantMessage);
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "An error occurred";
        setError(errorMsg);

        const errorMessage: Message = {
          id: uuidv4(),
          role: "assistant",
          content: `I'm sorry, I encountered an error processing your request. Please try again.\n\nError: ${errorMsg}`,
          timestamp: Date.now(),
          confidence_score: 0,
          flags: {
            LOW_CONFIDENCE: true,
            OUTDATED_POSSIBLE: false,
            JURISDICTION_NOTE: false,
            USE_OF_FORCE_CAUTION: false,
          },
        };
        addMessage(convId, errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [
      activeConversationId,
      createConversation,
      addMessage,
      setLoading,
      setError,
    ]
  );

  return {
    sendMessage,
    messages: activeConversation?.messages ?? [],
    isLoading,
    error,
  };
}
