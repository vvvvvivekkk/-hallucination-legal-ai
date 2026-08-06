"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import type { ChatMessage, Conversation, ConversationDetail, Message } from "@/lib/types";
import { extractError } from "@/lib/utils";

interface ChatState {
  conversations: Conversation[];
  activeConversation: ConversationDetail | null;
  messages: Message[];
  loading: boolean;
  streaming: boolean;
  error: string | null;
  sidebarOpen: boolean;
  pinnedOnly: boolean;
  searchQuery: string;
  loadConversations: () => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  createConversation: (title?: string) => Promise<string>;
  renameConversation: (id: string, title: string) => Promise<void>;
  togglePin: (id: string, pinned: boolean) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  stop: () => void;
  clearActive: () => void;
  setSidebarOpen: (open: boolean) => void;
  setPinnedOnly: (pinned: boolean) => void;
  setSearchQuery: (query: string) => void;
}

let abortController: AbortController | null = null;

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversation: null,
  messages: [],
  loading: false,
  streaming: false,
  error: null,
  sidebarOpen: true,
  pinnedOnly: false,
  searchQuery: "",

  async loadConversations() {
    const { pinnedOnly, searchQuery } = get();
    try {
      const data = await api.get<{ items: Conversation[]; total: number }>(
        "/api/conversations",
        { pinned: pinnedOnly, search: searchQuery || undefined, limit: 100 },
      );
      set({ conversations: data.items });
    } catch (error) {
      set({ error: extractError(error) });
    }
  },

  async loadConversation(id: string) {
    set({ loading: true, error: null });
    try {
      const detail = await api.get<ConversationDetail>(`/api/conversations/${id}`);
      set({ activeConversation: detail, messages: detail.messages, loading: false });
    } catch (error) {
      set({ loading: false, error: extractError(error) });
    }
  },

  async createConversation(title = "New chat") {
    const conversation = await api.post<Conversation>("/api/conversations", { title });
    await get().loadConversations();
    return conversation.id;
  },

  async renameConversation(id, title) {
    await api.patch<Conversation>(`/api/conversations/${id}`, { title });
    await get().loadConversations();
  },

  async togglePin(id, pinned) {
    await api.patch<Conversation>(`/api/conversations/${id}`, { is_pinned: pinned });
    await get().loadConversations();
  },

  async deleteConversation(id) {
    await api.delete(`/api/conversations/${id}`);
    if (get().activeConversation?.id === id) {
      set({ activeConversation: null, messages: [] });
    }
    await get().loadConversations();
  },

  async sendMessage(content) {
    const message = content.trim();
    if (!message || get().streaming) return;
    set({ error: null, streaming: true });
    let conversationId = get().activeConversation?.id;

    try {
      if (!conversationId) {
        const conversation = await api.post<Conversation>("/api/conversations", {
          title: message.slice(0, 80) || "New chat",
        });
        conversationId = conversation.id;
        set({ activeConversation: { ...conversation, messages: [] } });
      }
    } catch (error) {
      set({ error: extractError(error), streaming: false });
      return;
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      sources: [],
      citations: [],
      quality_score: 0,
      latency_ms: 0,
      tokens: 0,
      created_at: new Date().toISOString(),
    };
    set({ messages: [...get().messages, userMessage] });

    abortController = new AbortController();
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/conversations/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(sessionStorage.getItem("access_token")
            ? { Authorization: `Bearer ${sessionStorage.getItem("access_token")}` }
            : {}),
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
        credentials: "include",
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.error?.message ?? `Request failed (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantId = crypto.randomUUID();
      let assistantText = "";
      let finalPayload: Partial<ChatMessage> | null = null;

      set({
        messages: [
          ...get().messages,
          {
            id: assistantId,
            role: "assistant",
            content: "",
            sources: [],
            citations: [],
            quality_score: 0,
            latency_ms: 0,
            tokens: 0,
            created_at: new Date().toISOString(),
            streaming: true,
          } as Message,
        ],
      });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          let event: Record<string, unknown>;
          try {
            event = JSON.parse(line);
          } catch {
            continue;
          }
          if (event.type === "token") {
            assistantText += String(event.text ?? "");
            set({
              messages: get().messages.map((m) =>
                m.id === assistantId ? { ...m, content: assistantText } : m,
              ),
            });
          } else if (event.type === "result") {
            finalPayload = (event.result ?? {}) as Partial<ChatMessage>;
            assistantText = (finalPayload.content as string) ?? assistantText;
          } else if (event.type === "error") {
            set({ error: String(event.error ?? "Streaming failed") });
          }
        }
      }

      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer);
          if (event.type === "token") {
            assistantText += String(event.text ?? "");
          } else if (event.type === "result") {
            finalPayload = (event.result ?? {}) as Partial<ChatMessage>;
          }
        } catch {
          // ignore trailing partial
        }
      }

      const finalMessage: Message = {
        id: (finalPayload?.id as string) ?? assistantId,
        role: "assistant",
        content: assistantText || (finalPayload?.content as string) || "",
        sources: (finalPayload?.sources as Message["sources"]) ?? [],
        citations: (finalPayload?.citations as Message["citations"]) ?? [],
        verification: (finalPayload?.verification as Message["verification"]) ?? null,
        hallucination: (finalPayload?.hallucination as Message["hallucination"]) ?? null,
        confidence: (finalPayload?.confidence as Message["confidence"]) ?? null,
        quality_score: (finalPayload?.quality_score as number) ?? 0,
        latency_ms: (finalPayload?.latency_ms as number) ?? 0,
        tokens: (finalPayload?.tokens as number) ?? 0,
        created_at: new Date().toISOString(),
      };

      set({
        messages: get().messages.map((m) => (m.id === assistantId ? finalMessage : m)),
        streaming: false,
      });
      if (conversationId) {
        const detail = await api.get<ConversationDetail>(`/api/conversations/${conversationId}`);
        set({ activeConversation: detail, messages: detail.messages });
      }
      await get().loadConversations();
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        set({ streaming: false });
        return;
      }
      set({ error: extractError(error), streaming: false });
    }
  },

  stop() {
    abortController?.abort();
    abortController = null;
    set({ streaming: false });
  },

  clearActive() {
    set({ activeConversation: null, messages: [], error: null });
  },

  setSidebarOpen(open: boolean) {
    set({ sidebarOpen: open });
  },

  setPinnedOnly(pinned: boolean) {
    set({ pinnedOnly: pinned });
  },

  setSearchQuery(query: string) {
    set({ searchQuery: query });
  },
}));
