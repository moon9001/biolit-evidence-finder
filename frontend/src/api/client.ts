import type {
  DocumentItem,
  PageItem,
  SearchResponse,
  SettingsStatus,
  Stats,
} from '../types';

const API_BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, init);
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const body = await r.json();
      detail = body?.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const ctype = r.headers.get('content-type') || '';
  if (ctype.includes('application/json')) {
    return (await r.json()) as T;
  }
  return (await r.text()) as unknown as T;
}

export const api = {
  stats: () => request<Stats>('/stats'),

  listDocuments: () => request<DocumentItem[]>('/documents'),

  getDocument: (id: number) => request<DocumentItem>(`/documents/${id}`),

  deleteDocument: (id: number) =>
    request<{ deleted: number }>(`/documents/${id}`, { method: 'DELETE' }),

  uploadDocuments: async (files: File[]): Promise<DocumentItem[]> => {
    const fd = new FormData();
    for (const f of files) fd.append('files', f);
    return request<DocumentItem[]>('/documents/upload?auto_process=true', {
      method: 'POST',
      body: fd,
    });
  },

  reprocessDocument: (id: number) =>
    request<{ status: string; document_id: number }>(
      `/documents/${id}/process`,
      { method: 'POST' },
    ),

  listPages: (id: number) => request<PageItem[]>(`/documents/${id}/pages`),

  getPage: (id: number, page: number) =>
    request<PageItem>(`/documents/${id}/pages/${page}`),

  pageImageUrl: (id: number, page: number) =>
    `${API_BASE}/documents/${id}/page-image/${page}`,

  pdfFileUrl: (id: number, page?: number) =>
    page
      ? `${API_BASE}/documents/${id}/file#page=${page}`
      : `${API_BASE}/documents/${id}/file`,

  search: (q: string, mode: string, limit = 50) => {
    const params = new URLSearchParams({ q, mode, limit: String(limit) });
    return request<SearchResponse>(`/search?${params.toString()}`);
  },

  exportSearchUrl: (q: string, mode: string, format: 'csv' | 'json') => {
    const params = new URLSearchParams({ q, mode, format });
    return `${API_BASE}/export/search-results?${params.toString()}`;
  },

  settingsStatus: () => request<SettingsStatus>('/settings/status'),

  testLlm: () =>
    request<{ ok: boolean; status?: number; snippet?: string; error?: string; reason?: string }>(
      '/settings/test-llm',
      { method: 'POST' },
    ),

  updateSettings: (payload: Record<string, string | undefined>) =>
    request<SettingsStatus>('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
};
