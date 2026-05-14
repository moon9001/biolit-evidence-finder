import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useI18n } from '../i18n';
import type { SearchResponse } from '../types';

const MODES = [
  { value: 'exact', labelKey: 'search_exact' },
  { value: 'scientific', labelKey: 'search_scientific' },
  { value: 'fulltext', labelKey: 'search_fulltext' },
  { value: 'semantic', labelKey: 'search_semantic' },
  { value: 'hybrid', labelKey: 'search_hybrid' },
];

export default function Search() {
  const { t } = useI18n();
  const [q, setQ] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resp, setResp] = useState<SearchResponse | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.search(q.trim(), mode, 200);
      setResp(r);
      setPage(1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-forest-800">{t('search_title')}</h1>

      <form
        onSubmit={run}
        className="bg-white border border-stone-200 rounded-lg p-4 shadow-sm flex flex-col md:flex-row gap-2"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('search_placeholder')}
          className="flex-1 px-3 py-2 border border-stone-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-400"
        />
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="px-2 py-2 border border-stone-300 rounded bg-white"
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value}>
              {t(m.labelKey as any)}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={busy}
          className="px-4 py-2 rounded bg-forest-600 text-white hover:bg-forest-700 disabled:opacity-50"
        >
          {busy ? t('search_searching') : t('search_button')}
        </button>
      </form>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3 text-sm">
          {error}
        </div>
      )}

      {resp && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm text-stone-600">
            <div>
              {t('search_results', { count: resp.result_count })} <code className="text-forest-700">{resp.mode}</code>
              {resp.notes && (
                <span className="ml-2 text-amber-700">[{resp.notes}]</span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                className="px-2 py-1 border border-stone-300 rounded bg-white text-xs"
              >
                {[10, 20, 50, 100].map((n) => (
                  <option key={n} value={n}>{n}/page</option>
                ))}
              </select>
              <a
                href={api.exportSearchUrl(resp.query, resp.mode, 'csv')}
                className="text-forest-700 hover:underline"
              >
                {t('search_export_csv')}
              </a>
              <a
                href={api.exportSearchUrl(resp.query, resp.mode, 'json')}
                className="text-forest-700 hover:underline"
              >
                {t('search_export_json')}
              </a>
            </div>
          </div>

          <div className="bg-white border border-stone-200 rounded-lg overflow-x-auto shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-stone-600 text-left">
                <tr>
                  <th className="px-3 py-2">{t('search_col_document')}</th>
                  <th className="px-3 py-2">{t('search_col_page')}</th>
                  <th className="px-3 py-2">{t('search_col_match')}</th>
                  <th className="px-3 py-2">{t('search_col_type')}</th>
                  <th className="px-3 py-2">{t('search_col_score')}</th>
                  <th className="px-3 py-2">{t('search_col_context')}</th>
                  <th className="px-3 py-2">{t('search_col_view')}</th>
                </tr>
              </thead>
              <tbody>
                {resp.results.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center text-stone-500">
                      {t('search_no_results')}
                    </td>
                  </tr>
                )}
                {resp.results
                  .slice((page - 1) * pageSize, page * pageSize)
                  .map((r, i) => (
                  <tr key={i} className="border-t border-stone-100 align-top">
                    <td className="px-3 py-2">
                      <div className="font-medium text-stone-800">
                        {r.document_title || r.file_name}
                      </div>
                      <div className="text-xs text-stone-500">
                        {r.file_name} · #{r.document_id}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className="font-mono">{r.page_number}</span>
                    </td>
                    <td className="px-3 py-2 font-mono text-forest-700">
                      {r.matched_term}
                    </td>
                    <td className="px-3 py-2">
                      <span className="px-2 py-0.5 rounded text-xs bg-forest-50 text-forest-700 border border-forest-100">
                        {r.match_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono">
                      {r.score.toFixed(3)}
                    </td>
                    <td className="px-3 py-2 max-w-xl">
                      <Snippet text={r.context} term={r.matched_term} />
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={r.viewer_url}
                        className="text-forest-700 hover:underline whitespace-nowrap"
                      >
                        {t('search_view_original')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {resp.results.length > pageSize && (() => {
            const totalPages = Math.max(1, Math.ceil(resp.results.length / pageSize));
            const start = (page - 1) * pageSize + 1;
            const end = Math.min(resp.results.length, page * pageSize);
            return (
              <div className="flex items-center justify-between text-sm text-stone-600">
                <div>
                  {t('search_total', { start, end, total: resp.results.length })}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="px-3 py-1 rounded border border-stone-300 disabled:opacity-50 hover:bg-stone-50"
                  >
                    {t('search_prev')}
                  </button>
                  <span>
                    {t('documents_page_of', { page, pages: totalPages })}
                  </span>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="px-3 py-1 rounded border border-stone-300 disabled:opacity-50 hover:bg-stone-50"
                  >
                    {t('search_next')}
                  </button>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

function Snippet({ text, term }: { text: string; term: string }) {
  if (!text) return null;
  if (!term) return <span>{text}</span>;
  const ftsHl = text.replace(/<<([\s\S]+?)>>/g, '\u0001$1\u0002');
  const regex = new RegExp(
    term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
    'gi',
  );
  const withTerm = ftsHl.replace(regex, (m) => `\u0001${m}\u0002`);
  const parts = withTerm.split(/[\u0001\u0002]/);
  return (
    <span className="text-stone-700">
      {parts.map((p, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="hl">{p}</mark>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </span>
  );
}
