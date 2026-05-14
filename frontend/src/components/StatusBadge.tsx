interface Props {
  status: string;
}

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  pending: { label: '待处理', cls: 'bg-stone-200 text-stone-700' },
  queued: { label: '排队中', cls: 'bg-amber-100 text-amber-800' },
  processing: { label: '处理中', cls: 'bg-amber-100 text-amber-800 animate-pulse' },
  completed: { label: '已完成', cls: 'bg-forest-100 text-forest-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
};

export function StatusBadge({ status }: Props) {
  const m = STATUS_LABEL[status] ?? { label: status, cls: 'bg-stone-200' };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${m.cls}`}>
      {m.label}
    </span>
  );
}
