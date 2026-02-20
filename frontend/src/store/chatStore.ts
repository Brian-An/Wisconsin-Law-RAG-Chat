import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import type { Conversation, Message } from "@/lib/types";
import { STORAGE_KEY } from "@/lib/constants";
import { deriveTitle } from "@/lib/utils";

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;
  error: string | null;

  createConversation: () => string;
  setActiveConversation: (id: string | null) => void;
  deleteConversation: (id: string) => void;
  addMessage: (conversationId: string, message: Message) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  loadFromStorage: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeConversationId: null,
  isLoading: false,
  error: null,

  createConversation: () => {
    const id = uuidv4();
    const now = Date.now();
    const conversation: Conversation = {
      id,
      title: "New conversation",
      messages: [],
      session_id: uuidv4(),
      created_at: now,
      updated_at: now,
    };
    set((state) => ({
      conversations: [conversation, ...state.conversations],
      activeConversationId: id,
    }));
    return id;
  },

  setActiveConversation: (id) => {
    set({ activeConversationId: id });
  },

  deleteConversation: (id) => {
    set((state) => {
      const filtered = state.conversations.filter((c) => c.id !== id);
      return {
        conversations: filtered,
        activeConversationId:
          state.activeConversationId === id
            ? filtered[0]?.id ?? null
            : state.activeConversationId,
      };
    });
  },

  addMessage: (conversationId, message) => {
    set((state) => ({
      conversations: state.conversations.map((conv) => {
        if (conv.id !== conversationId) return conv;
        const messages = [...conv.messages, message];
        // Derive title from first user message
        const title =
          conv.messages.length === 0 && message.role === "user"
            ? deriveTitle(message.content)
            : conv.title;
        return { ...conv, messages, title, updated_at: Date.now() };
      }),
    }));
  },

  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  loadFromStorage: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const data = JSON.parse(raw) as {
          conversations: Conversation[];
          activeConversationId: string | null;
        };
        set({
          conversations: data.conversations,
          activeConversationId: data.activeConversationId,
        });
      }
    } catch {
      // Corrupt data — start fresh
    }
  },
}));

// Debounced persistence to localStorage
let persistTimer: ReturnType<typeof setTimeout>;
useChatStore.subscribe((state) => {
  clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          conversations: state.conversations,
          activeConversationId: state.activeConversationId,
        })
      );
    } catch {
      // localStorage full or unavailable
    }
  }, 300);
});
