import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  getStudioAuthToken,
  setStudioAuthToken,
  clearStudioAuthToken,
  getRequestHeaders,
  loginStudio,
  fetchDrafts,
  publishDraftToTelegram,
  checkAuthStatus,
  onAuthRequired,
} from "../api";

describe("Studio Authentication Client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("stores, retrieves, and clears the studio authentication token", () => {
    expect(getStudioAuthToken()).toBeNull();

    setStudioAuthToken("test_secret_token_123");
    expect(getStudioAuthToken()).toBe("test_secret_token_123");

    clearStudioAuthToken();
    expect(getStudioAuthToken()).toBeNull();
  });

  it("injects Authorization Bearer and X-Studio-Auth headers when token is set", () => {
    setStudioAuthToken("my_secure_token");
    const headers = getRequestHeaders();

    expect(headers["Authorization"]).toBe("Bearer my_secure_token");
    expect(headers["X-Studio-Auth"]).toBe("my_secure_token");
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("omits Authorization header when token is absent", () => {
    clearStudioAuthToken();
    const headers = getRequestHeaders();

    expect(headers["Authorization"]).toBeUndefined();
    expect(headers["X-Studio-Auth"]).toBeUndefined();
  });

  it("handles loginStudio success and stores returned token", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, token: "returned_auth_token_999" }),
    });

    const res = await loginStudio("input_password");
    expect(res.success).toBe(true);
    expect(getStudioAuthToken()).toBe("returned_auth_token_999");
  });

  it("handles loginStudio rejection with invalid token", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ success: false, error: "Invalid studio access token" }),
    });

    const res = await loginStudio("wrong_password");
    expect(res.success).toBe(false);
    expect(res.error).toBe("Invalid studio access token");
    expect(getStudioAuthToken()).toBeNull();
  });

  it("triggers onAuthRequired and clears token on 401 response during publish", async () => {
    setStudioAuthToken("expired_token");
    let authRequiredTriggered = false;
    const unsubscribe = onAuthRequired((req) => {
      authRequiredTriggered = req;
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ success: false, error: "Unauthorized" }),
    });

    const res = await publishDraftToTelegram({
      content_type: "ai_news" as any,
      title: "Test",
      body: "Test body",
    });

    expect(res.success).toBe(false);
    expect(res.error).toContain("Authentication required");
    expect(getStudioAuthToken()).toBeNull();
    expect(authRequiredTriggered).toBe(true);

    unsubscribe();
  });

  it("triggers onAuthRequired on 401 response during fetchDrafts", async () => {
    setStudioAuthToken("expired_token");
    let authRequiredTriggered = false;
    const unsubscribe = onAuthRequired((req) => {
      authRequiredTriggered = req;
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ success: false, error: "Unauthorized" }),
    });

    const drafts = await fetchDrafts();
    expect(Array.isArray(drafts)).toBe(true);
    expect(getStudioAuthToken()).toBeNull();
    expect(authRequiredTriggered).toBe(true);

    unsubscribe();
  });

  it("checkAuthStatus verifies token validity against /api/auth/verify", async () => {
    setStudioAuthToken("valid_token");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ authenticated: true, auth_required: true }),
    });

    const status = await checkAuthStatus();
    expect(status.authenticated).toBe(true);
    expect(status.authRequired).toBe(true);
  });
});
