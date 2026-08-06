import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatStore } from "@/stores/chat";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  };
});

const CONVERSATION = {
  id: "conv-1",
  title: "Statute of limitations",
  is_pinned: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("chat store", () => {
  beforeEach(() => {
    useChatStore.setState({
      conversations: [],
      activeConversation: null,
      messages: [],
      loading: false,
      streaming: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("loads conversations", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ items: [CONVERSATION], total: 1 });
    await useChatStore.getState().loadConversations();
    expect(useChatStore.getState().conversations).toHaveLength(1);
    expect(useChatStore.getState().conversations[0].title).toBe("Statute of limitations");
  });

  it("creates a conversation and refreshes the list", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce(CONVERSATION);
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ items: [CONVERSATION], total: 1 });
    const id = await useChatStore.getState().createConversation();
    expect(id).toBe("conv-1");
    expect(api.post).toHaveBeenCalledWith("/api/conversations", { title: "New chat" });
    expect(useChatStore.getState().conversations).toHaveLength(1);
  });

  it("toggles pin and reloads", async () => {
    (api.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ...CONVERSATION, is_pinned: true });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [{ ...CONVERSATION, is_pinned: true }],
      total: 1,
    });
    await useChatStore.getState().togglePin("conv-1", true);
    expect(api.patch).toHaveBeenCalledWith("/api/conversations/conv-1", { is_pinned: true });
    expect(useChatStore.getState().conversations[0].is_pinned).toBe(true);
  });
});
