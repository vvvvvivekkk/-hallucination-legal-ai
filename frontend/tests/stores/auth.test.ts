import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/auth";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      post: vi.fn(),
      get: vi.fn(),
      setTokens: vi.fn((tokens: { access_token: string }) => {
        sessionStorage.setItem("access_token", tokens.access_token);
      }),
      clearSession: vi.fn(() => {
        sessionStorage.removeItem("access_token");
      }),
    },
    fetchMe: vi.fn(),
  };
});

const MOCK_USER = {
  id: "user-1",
  email: "ada@example.com",
  full_name: "Ada Lovelace",
  role: "user",
  is_active: true,
};

const MOCK_TOKENS = {
  access_token: "access-1",
  refresh_token: "refresh-1",
  token_type: "bearer",
  expires_in: 3600,
  user: MOCK_USER,
};

describe("auth store", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, status: "idle", error: null });
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("login stores tokens and marks authenticated", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_TOKENS);
    await useAuthStore.getState().login("ada@example.com", "secret");
    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(useAuthStore.getState().user?.email).toBe("ada@example.com");
    expect(sessionStorage.getItem("access_token")).toBe("access-1");
  });

  it("login surfaces errors", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({
      response: { data: { error: { message: "Invalid credentials" } } },
    });
    await expect(
      useAuthStore.getState().login("ada@example.com", "wrong"),
    ).rejects.toBeTruthy();
    expect(useAuthStore.getState().error).toBe("Invalid credentials");
    expect(useAuthStore.getState().status).toBe("idle");
  });

  it("load marks unauthenticated when no token", async () => {
    await useAuthStore.getState().load();
    expect(useAuthStore.getState().status).toBe("unauthenticated");
  });

  it("logout clears session", async () => {
    useAuthStore.setState({ user: MOCK_USER, status: "authenticated" });
    sessionStorage.setItem("access_token", "access-1");
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});
    await useAuthStore.getState().logout();
    expect(useAuthStore.getState().status).toBe("unauthenticated");
    expect(sessionStorage.getItem("access_token")).toBeNull();
  });
});
