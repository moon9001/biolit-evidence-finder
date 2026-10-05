import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useI18n } from '../i18n';
import type { DocumentItem } from '../types';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function Upload() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(0);
  const [total, setTotal] = useState(0);
  const [startedAt, setStartedAt] = useState(0);

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files;
    if (!list) return;
    const arr: File[] = [];
    for (let i = 0; i < list.length; i++) arr.push(list[i]);
    setFiles(arr);
    setError(null);
  }

  function onDrop(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    const list = e.dataTransfer.files;
    if (!list) return;
    const arr: File[] = [];
    for (let i = 0; i < list.length; i++) {
      if (list[i].name.toLowerCase().endsWith('.pdf')) arr.push(list[i]);
    }
    if (arr.length) {
      setFiles(arr);
      setError(null);
    }
  }

  async function onUpload() {
    setError(null);
    if (!files.length) return;
    setBusy(true);
    setSent(0);
    setTotal(files.reduce((a, f) => a + f.size, 0));
    setStartedAt(Date.now());
    try {
      await api.uploadDocuments(files, (s, t) => {
        setSent(s);
        setTotal(t);
      });
      // Success - navigate to documents page to show progress
      navigate('/documents');
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const pct = total ? Math.min(100, Math.round((sent / total) * 100)) : 0;
  const elapsed = (Date.now() - startedAt) / 1000;
  const speed = elapsed > 0.2 ? sent / elapsed : 0;
  const eta = speed > 0 && total > sent ? (total - sent) / speed : 0;

  return (
    <div className="space-y-5">
      <section className="bg-white border border-stone-200 rounded-lg p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-forest-800">{t('upload_title')}</h1>
        <p className="text-stone-600 mt-1 text-sm">
          {t('upload_desc')}
        </p>

        <div className="mt-4 flex flex-col gap-3">
          <label
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            className="border-2 border-dashed border-forest-300 rounded-lg p-8 text-center cursor-pointer hover:bg-forest-50 transition"
          >
            <input
              type="file"
              multiple
              accept="application/pdf"
              className="hidden"
              onChange={onPick}
            />
            <div className="text-forest-700 font-medium">
              {t('upload_drag')}
            </div>
            <div className="text-xs text-stone-500 mt-1">
              {t('upload_only_pdf')}
            </div>
          </label>

          {files.length > 0 && (
            <div className="text-sm text-stone-700 border border-stone-200 rounded p-3 bg-stone-50">
              <div className="font-medium mb-1">
                {t('upload_selected', { count: files.length, size: formatBytes(files.reduce((a, f) => a + f.size, 0)) })}
              </div>
              <ul className="list-disc pl-5 max-h-40 overflow-y-auto">
                {files.map((f) => (
                  <li key={f.name}>
                    {f.name}{' '}
                    <span className="text-stone-500">({formatBytes(f.size)})</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <button
              type="button"
              onClick={onUpload}
              disabled={busy || files.length === 0}
              className="px-4 py-2 rounded bg-forest-600 text-white hover:bg-forest-700 disabled:opacity-50"
            >
              {busy ? t('upload_uploading') : t('upload_button')}
            </button>
          </div>

          {(busy || (sent > 0 && total > 0 && sent < total)) && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-stone-500">
                <span>
                  {t('upload_progress')}: {formatBytes(sent)} / {formatBytes(total)} ({pct}%)
                </span>
                <span>
                  {speed > 0 ? `${formatBytes(speed)}/s` : ''}
                  {eta > 0 ? ` · ${eta.toFixed(0)}s ${t('upload_remaining')}` : ''}
                </span>
              </div>
              <div className="h-2 bg-stone-200 rounded overflow-hidden">
                <div
                  className="h-full bg-forest-500 transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              {pct === 100 && (
                <div className="text-xs text-stone-500">
                  {t('upload_waiting')}
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3 text-sm">
              {error}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
