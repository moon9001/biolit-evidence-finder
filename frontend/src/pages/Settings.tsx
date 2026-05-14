import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { SettingsStatus } from '../types';

export default function Settings() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [llmBase, setLlmBase] = useState('');
  const [llmKey, setLlmKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [embBase, setEmbBase] = useState('');
  const [embKey, setEmbKey] = useState('');
  const [embModel, setEmbModel] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  async function load() {
    const s = await api.settingsStatus();
    setStatus(s);
    setLlmBase(s.llm_api_base_url);
    setLlmModel(s.llm_model);
    setEmbModel(s.embedding_model);
  }

  useEffect(() => {
    load();
  }, []);

  async function save() {
    setMsg(null);
    try {
      const r = await api.updateSettings({
        llm_api_base_url: llmBase || undefined,
        llm_api_key: llmKey || undefined,
        llm_model: llmModel || undefined,
        embedding_api_base_url: embBase || undefined,
        embedding_api_key: embKey || undefined,
        embedding_model: embModel || undefined,
      });
      setStatus(r);
      setMsg('已更新（仅本进程生效，重启后回退到 .env）');
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  async function test() {
    setTestResult('测试中...');
    const r = await api.testLlm();
    setTestResult(JSON.stringify(r));
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-forest-800">系统设置</h1>

      <section className="bg-white border border-stone-200 rounded-lg p-5 shadow-sm">
        <h2 className="font-semibold text-forest-700 mb-3">当前状态</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <Item label="LLM API" value={status?.llm_enabled ? '已启用' : '未配置'} />
          <Item label="Embedding API" value={status?.embedding_enabled ? '已启用' : '未配置'} />
          <Item label="本地 sentence-transformers" value={status?.embedding_local_available ? '可用' : '不可用'} />
          <Item label="本地 OCR (tesseract)" value={status?.ocr_local_available ? '可用' : '不可用'} />
          <Item label="DeepSeek-OCR" value={status?.deepseek_ocr_enabled ? '已配置' : '未配置'} />
        </div>
      </section>

      <section className="bg-white border border-stone-200 rounded-lg p-5 shadow-sm">
        <h2 className="font-semibold text-forest-700 mb-3">LLM API（OpenAI 兼容）</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <Field label="LLM_API_BASE_URL" value={llmBase} onChange={setLlmBase}
            placeholder="https://uni-api.cstcloud.cn/v1" />
          <Field label="LLM_API_KEY" value={llmKey} onChange={setLlmKey}
            placeholder="sk-..." type="password" />
          <Field label="LLM_MODEL" value={llmModel} onChange={setLlmModel}
            placeholder="deepseek-v4-flash" />
        </div>
        <div className="mt-3 flex gap-2 items-center">
          <button onClick={save} className="px-3 py-1.5 rounded bg-forest-600 text-white hover:bg-forest-700">保存</button>
          <button onClick={test} className="px-3 py-1.5 rounded border border-forest-600 text-forest-700 hover:bg-forest-50">测试连接</button>
          {testResult && <span className="text-xs text-stone-600 break-all">{testResult}</span>}
        </div>
      </section>

      <section className="bg-white border border-stone-200 rounded-lg p-5 shadow-sm">
        <h2 className="font-semibold text-forest-700 mb-3">Embedding API（OpenAI 兼容）</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <Field label="EMBEDDING_API_BASE_URL" value={embBase} onChange={setEmbBase}
            placeholder="https://uni-api.cstcloud.cn/v1" />
          <Field label="EMBEDDING_API_KEY" value={embKey} onChange={setEmbKey}
            placeholder="sk-..." type="password" />
          <Field label="EMBEDDING_MODEL" value={embModel} onChange={setEmbModel}
            placeholder="qwen3-embedding:8b" />
        </div>
        <div className="mt-3">
          <button onClick={save} className="px-3 py-1.5 rounded bg-forest-600 text-white hover:bg-forest-700">保存</button>
        </div>
      </section>

      {msg && <div className="text-sm text-stone-600">{msg}</div>}

      <p className="text-xs text-stone-500">
        永久生效请编辑 <code>backend/.env</code> 文件后重启服务。
        系统在 LLM/Embedding 不可用时仍保证 PDF 解析、规则抽取、关键词检索和 FTS 全文检索可用。
      </p>
    </div>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border border-stone-200 rounded p-2">
      <span className="text-stone-600">{label}</span>
      <span className="font-medium text-stone-800">{value}</span>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-stone-500">{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="px-2 py-1.5 border border-stone-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-400"
      />
    </label>
  );
}
