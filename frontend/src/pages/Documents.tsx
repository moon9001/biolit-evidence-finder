import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import type { DocumentItem } from '../types';

export default function Documents() {
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
    const t = window.setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  async function onReprocess(id: number) {
    await api.reprocessDocument(id);
    load();
  }

  async function onDelete(id: number) {
    if (!confirm('确认删除该 PDF 及其索引？')) return;
    await api.deleteDocument(id);
    load();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-forest-800">文献列表</h1>
        <Link
          to="/upload"
          className="text-sm px-3 py-1.5 rounded bg-forest-600 text-white hover:bg-forest-700"
        >
          + 新增上传
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
              <th className="px-3 py-2">文件名 / 标题</th>
              <th className="px-3 py-2">页数</th>
              <th className="px-3 py-2">状态</th>
              <th className="px-3 py-2">上传时间</th>
              <th className="px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-3 py-8 text-center text-stone-500"
                >
                  暂无文献，请先上传 PDF。
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
                <td className="px-3 py-2"><StatusBadge status={d.status} /></td>
                <td className="px-3 py-2 text-stone-600">
                  {new Date(d.created_at).toLocaleString()}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-2 text-xs">
                    <Link
                      to={`/viewer/${d.id}?page=1`}
                      className="text-forest-700 hover:underline"
                    >
                      查看页面
                    </Link>
                    <button
                      onClick={() => onReprocess(d.id)}
                      className="text-forest-700 hover:underline"
                    >
                      重新处理
                    </button>
                    <button
                      onClick={() => onDelete(d.id)}
                      className="text-red-600 hover:underline"
                    >
                      删除
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
