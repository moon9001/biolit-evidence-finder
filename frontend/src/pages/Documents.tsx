import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useI18n } from '../i18n';
import { StatusBadge } from '../components/StatusBadge';
import type { DocumentListResponse } from '../types';

const STATUS_TABS = [
  { key: '', labelKey: 'documents_filter_all' },
  { key: 'pending', labelKey: 'documents_filter_pending' },
  { key: 'queued', labelKey: 'documents_filter_queued' },
  { key: 'processing', labelKey: 'documents_filter_processing' },
  { key: 'completed', labelKey: 'documents_filter_completed' },
  { key: 'failed', labelKey: 'documents_filter_failed' },
];

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

export default function Documents() {
  const { t } = useI18n();
  const [resp, setResp] = useState<DocumentListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Debounce search input so we don't hammer the API while typing
  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(id);
  }, [search]);

  // Reset to first page when filters change
  useEffect(() => {
    setPage(1);
  }, [statusFilter, debouncedSearch, pageSize]);

  const loadingRef = useRef(false);

  async function load() {
    if (loadingRef.current) return;
    loadingRef.current = true;
    try {
      const r = await api.listDocuments({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        q: debouncedSearch || undefined,
      });
      setResp(r);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      loadingRef.current = false;
    }
  }

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 2000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, statusFilter, debouncedSearch]);

  async function onReprocess(id: number) {
    await api.reprocessDocument(id);
    load();
  }

  async function onDelete(id: number) {
    if (!confirm(t('documents_confirm_delete'))) return;
    await api.deleteDocument(id);
    load();
  }

  const totalPages = useMemo(() => {
    if (!resp) return 1;
    return Math.max(1, Math.ceil(resp.total / resp.page_size));
  }, [resp]);

  const counts = resp?.status_counts ?? {};
  const docs = resp?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-forest-800">{t('documents_title')}</h1>
        <Link
          to="/upload"
          className="text-sm px-3 py-1.5 rounded bg-forest-600 text-white hover:bg-forest-700"
        >
          {t('documents_new')}
        </Link>
      </div>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3 text-sm">
          {error}
        </div>
      )}

      {/* Filter bar */}
      <div className="bg-white border border-stone-200 rounded-lg shadow-sm p-3 space-y-3">
        <div className="flex flex-wrap items-center gap-1">
          {STATUS_TABS.map((tab) => {
            const c = tab.key ? counts[tab.key] ?? 0 : counts.all ?? 0;
            const active = statusFilter === tab.key;
            return (
              <button
                key={tab.key || 'all'}
                onClick={() => setStatusFilter(tab.key)}
                className={`px-3 py-1.5 rounded text-sm transition ${
                  active
                    ? 'bg-forest-600 text-white'
                    : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                }`}
              >
                {t(tab.labelKey as any)}
                <span
                  className={`ml-1.5 text-xs ${
                    active ? 'text-forest-100' : 'text-stone-500'
                  }`}
                >
                  {c}
                </span>
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('documents_search_placeholder')}
            className="flex-1 min-w-[200px] px-3 py-1.5 border border-stone-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-forest-400"
          />
          <div className="flex items-center gap-1 text-sm text-stone-600">
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="px-2 py-1 border border-stone-300 rounded bg-white"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <span>{t('documents_page_size')}</span>
          </div>
        </div>
      </div>

      <div className="bg-white border border-stone-200 rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-stone-50 text-stone-600 text-left">
            <tr>
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">{t('search_col_document')}</th>
              <th className="px-3 py-2">{t('documents_pages')}</th>
              <th className="px-3 py-2">{t('dashboard_status')}</th>
              <th className="px-3 py-2">{t('documents_uploaded')}</th>
              <th className="px-3 py-2">{t('search_col_view')}</th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-stone-500">
                  {t('documents_no_docs')}
                </td>
              </tr>
            )}
            {docs.map((d) => (
              <tr key={d.id} className="border-t border-stone-100">
                <td className="px-3 py-2 text-stone-500">{d.id}</td>
                <td className="px-3 py-2">
                  <div className="font-medium text-stone-800">
                    {d.title || d.file_name}
                  </div>
                  <div className="text-xs text-stone-500">{d.file_name}</div>
                  {d.error && (
                    <div className="text-xs text-red-600 mt-0.5">{d.error}</div>
                  )}
                </td>
                <td className="px-3 py-2">{d.page_count}</td>
                <td className="px-3 py-2 min-w-[180px]">
                  <StatusBadge status={d.status} />
                  {d.status === 'processing' && d.page_count > 0 && (
                    <div className="mt-1">
                      <div className="h-1.5 bg-stone-200 rounded overflow-hidden">
                        <div
                          className="h-full bg-forest-500 transition-all"
                          style={{
                            width: `${Math.min(
                              100,
                              Math.round(
                                ((d.processed_pages || 0) / d.page_count) * 100,
                              ),
                            )}%`,
                          }}
                        />
                      </div>
                      <div className="text-xs text-stone-500 mt-0.5">
                        {t('documents_parsing')} {d.processed_pages || 0} / {d.page_count}
                      </div>
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-stone-600">
                  {new Date(d.created_at).toLocaleString()}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-2 text-xs">
                    <Link
                      to={`/viewer/${d.id}?page=1`}
                      className="text-forest-700 hover:underline"
                    >
                      {t('documents_view')}
                    </Link>
                    <button
                      onClick={() => onReprocess(d.id)}
                      className="text-forest-700 hover:underline"
                    >
                      {t('documents_reprocess')}
                    </button>
                    <button
                      onClick={() => onDelete(d.id)}
                      className="text-red-600 hover:underline"
                    >
                      {t('documents_delete')}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {resp && resp.total > 0 && (
        <div className="flex items-center justify-between text-sm text-stone-600">
          <div>{t('documents_total', { count: resp.total })}</div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1 rounded border border-stone-300 disabled:opacity-50 hover:bg-stone-50"
            >
              {t('documents_prev')}
            </button>
            <span>
              {t('documents_page_of', { page: resp.page, pages: totalPages })}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-3 py-1 rounded border border-stone-300 disabled:opacity-50 hover:bg-stone-50"
            >
              {t('documents_next')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
