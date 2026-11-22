const LANGUAGE_LABELS: Record<string, string> = {
  c: 'C',
  java: 'Java',
  python: 'Python',
};

const LANGUAGE_COLORS: Record<string, string> = {
  c: 'bg-sky-100 text-sky-800',
  java: 'bg-orange-100 text-orange-800',
  python: 'bg-yellow-100 text-yellow-800',
};

export function LanguageBadge({ lang }: { lang: string }) {
  const label = LANGUAGE_LABELS[lang] || lang;
  const color = LANGUAGE_COLORS[lang] || 'bg-slate-100 text-slate-800';
  return <span className={`badge ${color}`}>{label}</span>;
}
