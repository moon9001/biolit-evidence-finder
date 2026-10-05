import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useI18n } from '../i18n';
import type { SettingsStatus, Stats } from '../types';

export default function Dashboard() {
  const { t } = useI18n();
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
    { labelKey: 'dashboard_pdf_count', value: stats?.document_count ?? 0 },
    { labelKey: 'dashboard_total_pages', value: stats?.page_count ?? 0 },
    { labelKey: 'dashboard_indexed_pages', value: stats?.indexed_pages ?? 0 },
    { labelKey: 'dashboard_names', value: stats?.occurrence_count ?? 0 },
    { labelKey: 'dashboard_chunks', value: stats?.chunk_count ?? 0 },
    { labelKey: 'dashboard_vectors', value: stats?.embedded_chunks ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-lg shadow-sm border border-stone-200 p-6">
        <h1 className="text-2xl font-semibold text-forest-800">
          {t('dashboard_title')}
        </h1>
        <p className="mt-2 text-stone-600 leading-relaxed">
          {t('dashboard_desc')}
        </p>
        <div className="mt-4 flex gap-3 text-sm">
          <Link
            to="/upload"
            className="px-4 py-2 rounded bg-forest-600 text-white hover:bg-forest-700"
          >
            {t('dashboard_upload')}
          </Link>
          <Link
            to="/search"
            className="px-4 py-2 rounded border border-forest-600 text-forest-700 hover:bg-forest-50"
          >
            {t('dashboard_search')}
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
            key={c.labelKey}
            className="bg-white rounded-lg border border-stone-200 p-4 shadow-sm"
          >
            <div className="text-stone-500 text-xs">{t(c.labelKey as any)}</div>
            <div className="text-2xl font-semibold text-forest-800 mt-1">
              {c.value}
            </div>
          </div>
        ))}
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-stone-200 p-5">
        <h2 className="text-lg font-semibold text-forest-800">{t('dashboard_status')}</h2>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <Capability
            ok={!!status?.llm_enabled}
            label={t('dashboard_llm')}
            detail={status?.llm_enabled 
              ? `${t('dashboard_llm_enabled')} · ${status.llm_model}` 
              : t('dashboard_llm_disabled')}
          />
          <Capability
            ok={!!status?.embedding_enabled || !!status?.embedding_local_available}
            label={t('dashboard_embedding')}
            detail={
              status?.embedding_enabled
                ? `${t('dashboard_embedding_api')} · ${status.embedding_model}`
                : status?.embedding_local_available
                  ? t('dashboard_embedding_local')
                  : t('dashboard_embedding_disabled')
            }
          />
          <Capability
            ok={!!status?.ocr_local_available}
            label={t('dashboard_ocr')}
            detail={status?.ocr_local_available ? t('dashboard_ocr_available') : t('dashboard_ocr_unavailable')}
          />
          <Capability
            ok={!!status?.deepseek_ocr_enabled}
            label={t('dashboard_deepseek_ocr')}
            detail={status?.deepseek_ocr_enabled ? t('dashboard_configured') : t('dashboard_not_configured')}
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
