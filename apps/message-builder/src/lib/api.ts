/**
 * Heyaaashu Studio API Client.
 * Connects Visual Editor to backend PostSchema API with authentication & local storage fallback.
 * Always resolves to relative same-origin `/api` by default in both development (via Vite proxy)
 * and production (via reverse proxy / aiohttp).
 */

import { DraftListItem, PostSchema } from '@/types/postSchema';

export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return '/api';
}

export const API_BASE_URL = getApiBaseUrl();

const LOCAL_STORAGE_KEY = 'heyaaashu_studio_drafts_v1';
const AUTH_TOKEN_KEY = 'heyaaashu_studio_auth_token';

export function getStudioAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setStudioAuthToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  }
}

export function clearStudioAuthToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

function getRequestHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  const token = getStudioAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Studio-Auth'] = token;
  }
  return headers;
}

export async function loginStudio(token: string): Promise<{ success: boolean; error?: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ token }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      setStudioAuthToken(data.token || token);
      return { success: true };
    }
    return { success: false, error: data.error || 'Authentication failed' };
  } catch (e: any) {
    return { success: false, error: e.message || 'Authentication request failed' };
  }
}

export async function fetchDrafts(): Promise<DraftListItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/drafts`, {
      headers: getRequestHeaders(),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.success && Array.isArray(data.drafts)) {
        return data.drafts;
      }
    }
  } catch (e) {
    console.warn('Backend API unavailable, using local drafts cache:', e);
  }

  // Fallback to localStorage
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    // ignore
  }
  return [];
}

export async function fetchDraftById(
  id: number
): Promise<{ schema: PostSchema; status: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/drafts/${id}`, {
      headers: getRequestHeaders(),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.success && data.schema) {
        return { schema: data.schema, status: data.status || 'draft' };
      }
    }
  } catch (e) {
    console.warn('Backend API unavailable:', e);
  }

  // Fallback
  const drafts = await fetchDrafts();
  const found = drafts.find((d) => d.post_id === id);
  if (found && found.raw_schema_json) {
    return {
      schema: JSON.parse(found.raw_schema_json),
      status: found.status,
    };
  }
  return null;
}

export async function saveDraftPost(
  post: PostSchema,
  draftId?: number
): Promise<{ success: boolean; draftId: number; error?: string }> {
  try {
    const url = draftId ? `${API_BASE_URL}/drafts/${draftId}` : `${API_BASE_URL}/drafts`;
    const method = draftId ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: getRequestHeaders(),
      body: JSON.stringify({ schema: post }),
    });

    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        return { success: true, draftId: data.draft_id || draftId };
      }
    } else {
      const errData = await res.json().catch(() => ({}));
      return {
        success: false,
        draftId: draftId || 0,
        error: errData.error || `HTTP ${res.status}: Failed to save draft`,
      };
    }
  } catch (e: any) {
    console.warn('Backend API failed, saving to local storage:', e);
  }

  // Fallback to local storage
  const id = draftId || Date.now();
  const drafts = await fetchDrafts();
  const existingIdx = drafts.findIndex((d) => d.post_id === id);

  const draftItem: DraftListItem = {
    post_id: id,
    content_type: post.content_type,
    title: post.title,
    text: post.body,
    status: 'draft',
    created_at: new Date().toISOString(),
    raw_schema_json: JSON.stringify(post),
  };

  if (existingIdx >= 0) {
    drafts[existingIdx] = draftItem;
  } else {
    drafts.unshift(draftItem);
  }

  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(drafts));
  return { success: true, draftId: id };
}

export async function deleteDraftById(id: number): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/drafts/${id}`, {
      method: 'DELETE',
      headers: getRequestHeaders(),
    });
    if (res.ok) return true;
  } catch (e) {
    // ignore
  }

  // Local storage cleanup
  const drafts = await fetchDrafts();
  const filtered = drafts.filter((d) => d.post_id !== id);
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(filtered));
  return true;
}

export async function publishDraftToTelegram(
  post: PostSchema,
  draftId?: number
): Promise<{ success: boolean; messageId?: number; channelId?: string; error?: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/publish`, {
      method: 'POST',
      headers: getRequestHeaders(),
      body: JSON.stringify({ schema: post, draft_id: draftId }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      return {
        success: false,
        error: errData.error || `HTTP ${res.status}: Publish rejected`,
      };
    }

    const data = await res.json();
    if (data && data.success) {
      return {
        success: true,
        messageId: data.message_id || data.publish_result?.message_id,
        channelId: data.channel_id || String(data.publish_result?.chat_id || ''),
      };
    }
    return { success: false, error: data?.error || 'Publish rejected by Telegram' };
  } catch (e: any) {
    console.error('Publish fetch error:', e);
    return { success: false, error: e.message || 'Failed to fetch' };
  }
}
