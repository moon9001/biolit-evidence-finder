import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { DocumentItem } from '../types';

export default function Upload() {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState<DocumentItem[]>([]);

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files;
    if (!list) return;
    const arr: File[] = [];
    for (let i = 0; i < list.length; i++) arr.push(list[i]);
    setFiles(arr);
  }

  async function onUpload() {
    setError(null);
    if (!files.length) return;
    setBusy(true);
    try {
      const res = await api.uploadDocuments(files);
      setUploaded(res);
      setFiles([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <section className="bg-white border border-stone-200 rounded-lg p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-forest-800">上传 PDF 文献</h1>
        <p className="text-stone-600 mt-1 text-sm">
          支持多个 PDF 同时上传。上传后系统会自动开始页级解析；扫描型 PDF 需要安装本地 tesseract 以启用 OCR。
        </p>

        <div className="mt-4 flex flex-col gap-3">
          <label className="border-2 border-dashed border-forest-300 rounded-lg p-8 text-center cursor-pointer hover:bg-forest-50 transition">
            <input
              type="file"
              multiple
              accept="application/pdf"
              className="hidden"
              onChange={onPick}
            />
            <div className="text-forest-700 font-medium">
              点击或拖拽 PDF 到此处选择文件
            </div>
            <div className="text-xs text-stone-500 mt-1">
              仅接受 .pdf 文件
            </div>
          </label>

          {files.length > 0 && (
            <ul className="text-sm text-stone-700 list-disc pl-5">
              {files.map((f) => (
                <li key={f.name}>
                  {f.name} <span className="text-stone-500">({Math.round(f.size / 1024)} KB)</span>
                </li>
              ))}
            </ul>
          )}

          <div>
            <button
              type="button"
              onClick={onUpload}
              disabled={busy || files.length === 0}
              className="px-4 py-2 rounded bg-forest-600 text-white hover:bg-forest-700 disabled:opacity-50"
            >
              {busy ? '上传中...' : '上传并开始解析'}
            </button>
          </div>

          {error && (
            <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3 text-sm">
              {error}
            </div>
          )}
        </div>
      </section>

      {uploaded.length > 0 && (
        <section className="bg-white border border-stone-200 rounded-lg p-5 shadow-sm">
          <h2 className="text-base font-semibold text-forest-800">本次上传</h2>
          <ul className="mt-2 divide-y divide-stone-100">
            {uploaded.map((d) => (
              <li
                key={d.id}
                className="py-2 flex items-center justify-between text-sm"
              >
                <span>
                  <span className="font-medium">{d.file_name}</span>{' '}
                  <span className="text-stone-500">#{d.id}</span>
                </span>
                <Link
                  to="/documents"
                  className="text-forest-700 hover:underline"
                >
                  前往文献列表查看处理状态 →
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
