import { beforeEach, describe, expect, it } from "vitest";
import { ApiError, api, getCsrfToken } from "@/lib/api";

function mockRejectionOnce(error: unknown) {
  api.instance.defaults.adapter = async () => {
    throw error;
  };
}

describe("ApiError", () => {
  it("parses the backend error envelope", async () => {
    mockRejectionOnce({
      response: {
        status: 409,
        data: { error: { code: "email_taken", message: "Email already registered" } },
      },
      message: "Request failed",
    });

    await expect(api.get("/api/auth/me")).rejects.toMatchObject({
      status: 409,
      code: "email_taken",
      message: "Email already registered",
    });
  });

  it("is an instance of ApiError", async () => {
    mockRejectionOnce({
      response: { status: 500, data: { error: { code: "internal", message: "boom" } } },
    });
    try {
      await api.get("/x");
      throw new Error("expected request to reject");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
    }
  });
});

describe("getCsrfToken", () => {
  beforeEach(() => {
    document.cookie = "csrf_token=abc123; path=/";
  });

  it("reads the CSRF cookie", () => {
    expect(getCsrfToken()).toBe("abc123");
  });
});
