export function LocationControl({ active, locating, error, onLocate, onClear }) {
  return (
    <div className="flex flex-col gap-2">
      {active ? (
        <div className="rounded-md border-2 border-brand bg-brand-tint p-3">
          <p className="text-base font-bold text-brand">Using your location</p>
          <p className="text-sm text-ink-soft">
            Facilities are measured from where you are. Your location is used only for
            this search.
          </p>
          <button
            type="button"
            onClick={onClear}
            className="mt-2 text-base font-bold text-brand underline underline-offset-2 hover:text-brand-dark"
          >
            Stop using my location
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={onLocate}
          disabled={locating}
          className="w-full rounded-md border-2 border-brand bg-brand px-3 py-2.5 text-base font-bold text-white hover:bg-brand-dark disabled:cursor-wait disabled:opacity-70"
        >
          {locating ? "Finding your location…" : "Use my location"}
        </button>
      )}
      {error && (
        <p role="alert" className="text-base font-bold text-alert">
          {error}
        </p>
      )}
    </div>
  );
}
