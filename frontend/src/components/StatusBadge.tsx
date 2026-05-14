import { useI18n } from '../i18n';

interface Props {
  status: string;
}

export function StatusBadge({ status }: Props) {
  const { t } = useI18n();
  
  const statusConfig: Record<string, { labelKey: string; cls: string }> = {
    pending: { labelKey: 'status_pending', cls: 'bg-stone-200 text-stone-700' },
    queued: { labelKey: 'status_queued', cls: 'bg-amber-100 text-amber-800' },
    processing: { labelKey: 'status_processing', cls: 'bg-amber-100 text-amber-800 animate-pulse' },
    completed: { labelKey: 'status_completed', cls: 'bg-forest-100 text-forest-700' },
    failed: { labelKey: 'status_failed', cls: 'bg-red-100 text-red-700' },
  };

  const config = statusConfig[status] ?? { labelKey: status as any, cls: 'bg-stone-200' };
  
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.cls}`}>
      {t(config.labelKey as any)}
    </span>
  );
}
