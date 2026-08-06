import { describe, expect, it } from "vitest";
import {
  cn,
  extractError,
  formatBytes,
  getConfidenceColor,
  timeAgo,
  truncate,
} from "@/lib/utils";

describe("cn", () => {
  it("merges class names and resolves conflicts", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("a", "b")).toBe("a b");
  });
});

describe("formatBytes", () => {
  it("formats bytes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(1048576)).toBe("1 MB");
  });
});

describe("truncate", () => {
  it("truncates long strings", () => {
    expect(truncate("a".repeat(200), 10)).toMatch(/^a{10}\.\.\.$/);
    expect(truncate("short")).toBe("short");
  });
});

describe("timeAgo", () => {
  it("handles empty input", () => {
    expect(timeAgo(null)).toBe("");
    expect(timeAgo("")).toBe("");
  });
  it("returns just now for recent timestamps", () => {
    expect(timeAgo(new Date().toISOString())).toBe("just now");
  });
});

describe("getConfidenceColor", () => {
  it("returns color by threshold", () => {
    expect(getConfidenceColor(0.9)).toContain("emerald");
    expect(getConfidenceColor(0.7)).toContain("amber");
    expect(getConfidenceColor(0.3)).toContain("red");
  });
});

describe("extractError", () => {
  it("parses the backend error envelope", () => {
    const error = {
      response: { data: { error: { message: "Invalid credentials" } } },
    };
    expect(extractError(error)).toBe("Invalid credentials");
  });
  it("falls back to Error message", () => {
    expect(extractError(new Error("boom"))).toBe("boom");
  });
  it("returns default for unknown", () => {
    expect(extractError(undefined)).toBe("Something went wrong. Please try again.");
  });
});
