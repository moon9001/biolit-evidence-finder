import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import type { DocumentItem, PageItem } from '../types';

export default function Viewer() {
  const { docId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const id = Number(docId);
  const page = Number(searchParams.get('page') || '1');
  const q = searchParams.get('q') || '';

  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [pageData, setPageData] = useState<PageItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [d, p] = await Promise.all([
          api.getDocument(id),
          api.getPage(id, page),
        ]);
        if (!cancelled) {
          setDoc(d);
          setPageData(p);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id, page]);

  function gotoPage(n: number) {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(n));
    setSearchParams(next);
  }

  const pageCount = doc?.page_count ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-forest-800">
            {doc?.title || doc?.file_name || `Document #${id}`}
          </h1>
          <div className="text-xs text-stone-500">
            {doc?.file_name} · 共 {pageCount} 页 · 当前 {page} 页
            {q && (
              <span className="ml-2">
                · 关键词 <code className="text-forest-700">{q}</code>
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => gotoPage(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="px-2 py-1 rounded border border-stone-300 disabled:opacity-50"
          >
            ← 上一页
          </button>
          <input
            type="number"
            min={1}
            max={pageCount || undefined}
            value={page}
            onChange={(e) => gotoPage(Math.max(1, Number(e.target.value) || 1))}
            className="w-16 px-2 py-1 border border-stone-300 rounded text-center"
          />
          <span className="text-stone-500">/ {pageCount}</span>
          <button
            onClick={() => gotoPage(Math.min(pageCount || page + 1, page + 1))}
            disabled={!!pageCount && page >= pageCount}
            className="px-2 py-1 rounded border border-stone-300 disabled:opacity-50"
          >
            下一页 →
          </button>
          <a
            href={api.pdfFileUrl(id, page)}
            target="_blank"
            rel="noreferrer"
            className="px-3 py-1.5 rounded bg-forest-600 text-white hover:bg-forest-700"
          >
            打开原始 PDF
          </a>
          <Link
            to="/search"
            className="px-3 py-1.5 rounded border border-stone-300 hover:bg-stone-50"
          >
            返回检索
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-stone-200 rounded-lg p-3 shadow-sm">
          <div className="text-xs text-stone-500 mb-2">页面截图</div>
          <div className="bg-stone-100 rounded overflow-hidden flex items-center justify-center min-h-[400px]">
            <img
              src={api.pageImageUrl(id, page)}
              alt={`page ${page}`}
              className="max-w-full max-h-[80vh] object-contain"
              onError={(e) =>
                ((e.currentTarget as HTMLImageElement).style.display = 'none')
              }
            />
          </div>
        </div>

        <div className="bg-white border border-stone-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-stone-500">
              页面文本 {pageData?.ocr_used ? '(来自 OCR)' : ''}
            </div>
            <div className="text-xs text-stone-400">
              {pageData?.text_length ?? 0} 字符
            </div>
          </div>
          <PageText text={pageData?.text || ''} term={q} />
        </div>
      </div>
    </div>
  );
}

function PageText({ text, term }: { text: string; term: string }) {
  const html = useMemo(() => {
    if (!text) return null;
    if (!term) {
      return text.split(/\n/).map((line, i) => (
        <p key={i} className="text-sm leading-relaxed text-stone-800">
          {line || '\u00A0'}
        </p>
      ));
    }
    const re = new RegExp(
      term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
      'gi',
    );
    return text.split(/\n/).map((line, i) => {
      const parts: Array<string | { hl: string }> = [];
      let last = 0;
      let m: RegExpExecArray | null;
      const r = new RegExp(re.source, re.flags);
      while ((m = r.exec(line))) {
        if (m.index > last) parts.push(line.slice(last, m.index));
        parts.push({ hl: m[0] });
        last = m.index + m[0].length;
        if (m[0].length === 0) r.lastIndex++;
      }
      if (last < line.length) parts.push(line.slice(last));
      return (
        <p key={i} className="text-sm leading-relaxed text-stone-800">
          {parts.length === 0 ? '\u00A0' : parts.map((p, j) =>
            typeof p === 'string' ? (
              <span key={j}>{p}</span>
            ) : (
              <mark key={j} className="hl">{p.hl}</mark>
            ),
          )}
        </p>
      );
    });
  }, [text, term]);
  if (!text) return <div className="text-stone-400 text-sm">本页无文本</div>;
  return <div className="max-h-[78vh] overflow-y-auto pr-2">{html}</div>;
}
