export function LoadingSpinner() {
  return (
    <div className="p-10 text-center text-slate-400">
      <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600 mr-2 align-middle"></div>
      <span>Loading…</span>
    </div>
  );
}
