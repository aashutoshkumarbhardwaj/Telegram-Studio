/**
 * Heyaaashu Studio API Client.
 * Connects Visual Editor to backend PostSchema API with local storage fallback.
 */

import { DraftListItem, PostSchema } from '@/types/postSchema';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const LOCAL_STORAGE_KEY = 'heyaaashu_studio_drafts_v1';

export async function fetchDrafts(): Promise<DraftListItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/drafts`);
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

export async function fetchDraftById(id: number): Promise<{ schema: PostSchema; status: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/drafts/${id}`);
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema: post }),
    });

    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        return { success: true, draftId: data.draft_id || draftId };
      }
    } else {
      const errData = await res.json().catch(() => ({}));
      return { success: false, draftId: draftId || 0, error: errData.error || 'Failed to save draft' };
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
    const res = await fetch(`${API_BASE_URL}/drafts/${id}`, { method: 'DELETE' });
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
): Promise<{ success: boolean; messageId?: number; error?: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema: post, draft_id: draftId }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      return { success: true, messageId: data.publish_result?.message_id };
    }
    return { success: false, error: data.error || 'Publish rejected by Telegram' };
  } catch (e: any) {
    return { success: false, error: e.message || 'Network error communicating with publisher' };
  }
}
