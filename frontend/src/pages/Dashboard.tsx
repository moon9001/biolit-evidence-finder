import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { SettingsStatus, Stats } from '../types';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: number | undefined;
    async function load() {
      try {
        const [s, st] = await Promise.all([
          api.stats(),
          api.settingsStatus(),
        ]);
        setStats(s);
        setStatus(st);
      } catch (e) {
        setError((e as Error).message);
      }
    }
    load();
    timer = window.setInterval(load, 5000);
    return () => {
      if (timer) clearInterval(timer);
    };
  }, []);

  const cards = [
    { label: 'PDF 数量', value: stats?.document_count ?? 0 },
    { label: '总页数', value: stats?.page_count ?? 0 },
    { label: '已索引页面', value: stats?.indexed_pages ?? 0 },
    { label: '已抽取名称 / 关键词', value: stats?.occurrence_count ?? 0 },
    { label: '语义切片', value: stats?.chunk_count ?? 0 },
    { label: '已生成向量', value: stats?.embedded_chunks ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-lg shadow-sm border border-stone-200 p-6">
        <h1 className="text-2xl font-semibold text-forest-800">
          BioLitEvidence Finder
        </h1>
        <p className="mt-2 text-stone-600 leading-relaxed">
          面向植物分类学、生物多样性文献、志书与图谱的页级证据发现工具。
          上传 PDF 后系统会按页解析文本、识别拉丁学名与中文关键词，
          并在检索时返回每条命中的 PDF、页码、上下文和原文回查链接。
        </p>
        <div className="mt-4 flex gap-3 text-sm">
          <Link
            to="/upload"
            className="px-4 py-2 rounded bg-forest-600 text-white hover:bg-forest-700"
          >
            上传 PDF
          </Link>
          <Link
            to="/search"
            className="px-4 py-2 rounded border border-forest-600 text-forest-700 hover:bg-forest-50"
          >
            开始检索
          </Link>
        </div>
      </section>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3">
          {error}
        </div>
      )}

      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="bg-white rounded-lg border border-stone-200 p-4 shadow-sm"
          >
            <div className="text-stone-500 text-xs">{c.label}</div>
            <div className="text-2xl font-semibold text-forest-800 mt-1">
              {c.value}
            </div>
          </div>
        ))}
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-stone-200 p-5">
        <h2 className="text-lg font-semibold text-forest-800">系统能力状态</h2>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <Capability
            ok={!!status?.llm_enabled}
            label="LLM 辅助抽取"
            detail={status?.llm_enabled ? `已启用 · ${status.llm_model}` : '未配置（规则抽取仍可用）'}
          />
          <Capability
            ok={!!status?.embedding_enabled || !!status?.embedding_local_available}
            label="语义向量"
            detail={
              status?.embedding_enabled
                ? `API 已启用 · ${status.embedding_model}`
                : status?.embedding_local_available
                  ? '本地 sentence-transformers 可用'
                  : '未启用（关键词检索仍可用）'
            }
          />
          <Capability
            ok={!!status?.ocr_local_available}
            label="本地 OCR (tesseract)"
            detail={status?.ocr_local_available ? '可用' : '不可用，扫描页将跳过 OCR'}
          />
          <Capability
            ok={!!status?.deepseek_ocr_enabled}
            label="DeepSeek-OCR"
            detail={status?.deepseek_ocr_enabled ? '已配置' : '未配置（可选）'}
          />
        </div>
      </section>
    </div>
  );
}

function Capability({
  ok,
  label,
  detail,
}: {
  ok: boolean;
  label: string;
  detail: string;
}) {
  return (
    <div className="flex items-center justify-between border border-stone-200 rounded p-3">
      <div>
        <div className="font-medium text-stone-800">{label}</div>
        <div className="text-xs text-stone-500 mt-0.5">{detail}</div>
      </div>
      <span
        className={`px-2 py-0.5 rounded text-xs font-medium ${
          ok ? 'bg-forest-100 text-forest-700' : 'bg-stone-200 text-stone-600'
        }`}
      >
        {ok ? 'on' : 'off'}
      </span>
    </div>
  );
}
