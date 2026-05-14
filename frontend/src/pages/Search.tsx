import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { SearchResponse } from '../types';

const MODES = [
  { value: 'exact', label: '精确检索' },
  { value: 'scientific', label: '学名检索' },
  { value: 'fulltext', label: '全文检索 (FTS)' },
  { value: 'semantic', label: '语义检索' },
  { value: 'hybrid', label: '混合检索' },
];

export default function Search() {
  const [q, setQ] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resp, setResp] = useState<SearchResponse | null>(null);

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.search(q.trim(), mode, 100);
      setResp(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-forest-800">页级证据检索</h1>

      <form
        onSubmit={run}
        className="bg-white border border-stone-200 rounded-lg p-4 shadow-sm flex flex-col md:flex-row gap-2"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="输入物种名、关键词或自然语言问题，例如 Camellia sinensis、云南山茶分布"
          className="flex-1 px-3 py-2 border border-stone-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-400"
        />
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="px-2 py-2 border border-stone-300 rounded bg-white"
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={busy}
          className="px-4 py-2 rounded bg-forest-600 text-white hover:bg-forest-700 disabled:opacity-50"
        >
          {busy ? '检索中...' : '检索'}
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
              共找到 <strong>{resp.result_count}</strong> 条结果，模式：
              <code className="text-forest-700">{resp.mode}</code>
              {resp.notes && (
                <span className="ml-2 text-amber-700">[{resp.notes}]</span>
              )}
            </div>
            <div className="flex gap-3">
              <a
                href={api.exportSearchUrl(resp.query, resp.mode, 'csv')}
                className="text-forest-700 hover:underline"
              >
                导出 CSV
              </a>
              <a
                href={api.exportSearchUrl(resp.query, resp.mode, 'json')}
                className="text-forest-700 hover:underline"
              >
                导出 JSON
              </a>
            </div>
          </div>

          <div className="bg-white border border-stone-200 rounded-lg overflow-x-auto shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-stone-600 text-left">
                <tr>
                  <th className="px-3 py-2">文献</th>
                  <th className="px-3 py-2">页码</th>
                  <th className="px-3 py-2">命中</th>
                  <th className="px-3 py-2">类型</th>
                  <th className="px-3 py-2">分数</th>
                  <th className="px-3 py-2">上下文</th>
                  <th className="px-3 py-2">原文</th>
                </tr>
              </thead>
              <tbody>
                {resp.results.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center text-stone-500">
                      没有命中结果
                    </td>
                  </tr>
                )}
                {resp.results.map((r, i) => (
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
                        查看原文 →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Snippet({ text, term }: { text: string; term: string }) {
  if (!term) return <span>{text}</span>;
  // Highlight all (case-insensitive) occurrences of term, plus <<...>> coming
  // from FTS5 snippet().
  const ftsHl = text
    .replace(/<<([\s\S]+?)>>/g, '\u0001$1\u0002');
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
