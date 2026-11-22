import { Indicator } from '../types';

export function IndicatorsList({ items }: { items?: Indicator[] }) {
  if (!items?.length) {
    return <span className="text-xs text-slate-400">None</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((item) => (
        <span
          key={item.code}
          title={item.detail}
          className="badge bg-amber-100 text-amber-900"
        >
          {item.label}
        </span>
      ))}
    </div>
  );
}
