const STATUS_CONFIG: Record<string, [string, string]> = {
  not_started: ['Not started', 'bg-slate-100 text-slate-600'],
  in_progress: ['In progress', 'bg-amber-100 text-amber-800'],
  submitted: ['Submitted', 'bg-blue-100 text-blue-800'],
  correction: ['Correction requested', 'bg-rose-100 text-rose-800'],
  approved: ['Approved', 'bg-emerald-100 text-emerald-800'],
};

export function StatusBadge({ status }: { status: string }) {
  const [label, colorClass] = STATUS_CONFIG[status] || [status, 'bg-slate-100 text-slate-600'];
  return <span className={`badge ${colorClass}`}>{label}</span>;
}
