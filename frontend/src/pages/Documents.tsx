import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useI18n } from '../i18n';
import { StatusBadge } from '../components/StatusBadge';
import type { DocumentItem } from '../types';

export default function Documents() {
  const { t } = useI18n();
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setDocs(await api.listDocuments());
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 2000);
    return () => clearInterval(interval);
  }, []);

  async function onReprocess(id: number) {
    await api.reprocessDocument(id);
    load();
  }

  async function onDelete(id: number) {
    if (!confirm(t('documents_confirm_delete'))) return;
    await api.deleteDocument(id);
    load();
  }

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
    </div>
  );
}
