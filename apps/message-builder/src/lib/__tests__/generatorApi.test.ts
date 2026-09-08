import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { generatePostFromInput, generateHookOptions, setStudioAuthToken, clearStudioAuthToken } from '../api';

describe('AI Generator API Client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('sends POST /api/generate with authorization and returns structured result', async () => {
    setStudioAuthToken('valid_studio_token');

    const mockResponse = {
      success: true,
      draft_id: 42,
      post: {
        schema_version: '1.0.0',
        content_type: 'ai_news',
        title: 'Google Announces Gemini 2.0',
        body: 'Gemini 2.0 body text with takeaways...',
        parse_mode: 'HTML',
      },
      quality: {
        hook: 92,
        clarity: 90,
        value: 95,
        readability: 91,
        source: 100,
        completeness: 94,
        overall: 93,
        status: 'ready',
      },
      generation: {
        input_type: 'url',
        detected_category: 'ai_news',
        category_confidence: 0.95,
        category_review_needed: false,
        hooks: [
          { text: 'Google Announces Gemini 2.0', score: 93, style: 'punchy' },
          { text: 'Gemini 2.0 Signals Major AI Shift', score: 88, style: 'context' },
        ],
        source_name: 'Google Blog',
      },
      visual: {
        needs_visual: true,
        concept: 'Minimalist editorial graphic...',
      },
    };

    let capturedHeaders: any = null;
    let capturedBody: any = null;

    globalThis.fetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      capturedHeaders = init.headers;
      capturedBody = JSON.parse(init.body);
      return {
        ok: true,
        status: 200,
        json: async () => mockResponse,
      };
    });

    const res = await generatePostFromInput({
      input: 'https://blog.google/gemini-2',
      category: 'ai_news',
      notes: 'Focus on benchmarks',
    });

    expect(res.success).toBe(true);
    expect(res.draft_id).toBe(42);
    expect(res.post?.title).toBe('Google Announces Gemini 2.0');
    expect(res.quality?.overall).toBe(93);
    expect(capturedHeaders['Authorization']).toBe('Bearer valid_studio_token');
    expect(capturedBody.input).toBe('https://blog.google/gemini-2');
    expect(capturedBody.category).toBe('ai_news');
  });

  it('gracefully falls back to client smart extractor on server URL error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        success: false,
        error: "Couldn't read this URL.",
        url_error: true,
      }),
    });

    const res = await generatePostFromInput({
      input: 'https://broken-domain.invalid',
    });

    // Gracefully recovers with smartExtractor instead of blocking the user
    expect(res.success).toBe(true);
    expect(res.post).toBeDefined();
    expect(res.post?.buttons).toBeDefined();
  });

  it('calls POST /api/generate/hook to retrieve alternative hooks', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        hooks: [
          { text: 'Option 1', score: 90, style: 'punchy' },
          { text: 'Option 2', score: 85, style: 'scale' },
        ],
      }),
    });

    const res = await generateHookOptions('Title', 'Body text', 'ai_news');
    expect(res.success).toBe(true);
    expect(res.hooks?.length).toBe(2);
  });
});
