import { describe, it, expect } from "vitest";
import { getApiBaseUrl } from "../api";

describe("API Base URL configuration", () => {
  it("defaults to relative same-origin /api", () => {
    const url = getApiBaseUrl();
    expect(url).toBe("/api");
    expect(url).not.toContain("127.0.0.1");
    expect(url).not.toContain("localhost");
    expect(url).not.toContain(":8000");
  });

  it("never resolves to 127.0.0.1:8000 in production", () => {
    const url = getApiBaseUrl();
    expect(url.startsWith("/api")).toBe(true);
  });
});
