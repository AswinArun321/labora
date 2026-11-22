export function Logo({ small = false }: { small?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`grid place-items-center rounded-lg bg-brand-600 font-bold text-white ${
          small ? 'h-7 w-7 text-sm' : 'h-10 w-10 text-lg'
        }`}
      >
        L
      </div>
      <div>
        <div className={`font-bold tracking-tight text-slate-900 ${small ? 'text-base' : 'text-2xl'}`}>
          LABORA
        </div>
        {!small && (
          <div className="text-xs text-slate-500">
            Write. Execute. Verify. Record.
          </div>
        )}
      </div>
    </div>
  );
}
