export function ErrorAlert({ error }: { error: any }) {
  if (!error) return null;
  const message =
    error.data && typeof error.data === 'object' && !error.data.detail
      ? JSON.stringify(error.data)
      : error.message || String(error);

  return (
    <div className="mb-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 ring-1 ring-rose-200">
      {message}
    </div>
  );
}
