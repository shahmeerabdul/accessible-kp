const OWNERSHIP_OPTIONS = [
  { value: "", label: "All" },
  { value: "government", label: "Govt" },
  { value: "private", label: "Private" },
];

function TogglePill({ active, onClick, children, title }) {
  return (
    <button
      type="button"
      onClick={() => onClick(!active)}
      aria-pressed={active}
      title={title}
      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
        active
          ? "border-brand-500/60 bg-brand-500/15 text-brand-200 shadow-sm shadow-brand-500/20"
          : "border-slate-700/80 bg-slate-950/60 text-slate-400 hover:border-slate-600 hover:text-slate-200"
      }`}
    >
      {children}
    </button>
  );
}

export function Filters({
  ownership,
  setOwnership,
  emergencyOnly,
  setEmergencyOnly,
  open24,
  setOpen24,
  limit,
  setLimit,
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Ownership
        </span>
        <div className="grid grid-cols-3 gap-1 rounded-lg border border-slate-700/80 bg-slate-950/60 p-1">
          {OWNERSHIP_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setOwnership(opt.value)}
              aria-pressed={ownership === opt.value}
              className={`rounded-md px-2 py-1.5 text-xs font-medium transition ${
                ownership === opt.value
                  ? "bg-brand-500/20 text-brand-200 shadow-sm"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Quick filters
        </span>
        <div className="flex flex-wrap gap-2">
          <TogglePill
            active={emergencyOnly}
            onClick={setEmergencyOnly}
            title="Only facilities tagged as having emergency services"
          >
            Emergency
          </TogglePill>
          <TogglePill
            active={open24}
            onClick={setOpen24}
            title="Only facilities tagged as open 24/7"
          >
            Open 24/7
          </TogglePill>
        </div>
        <p className="text-[10px] leading-relaxed text-slate-500">
          Based on OpenStreetMap tags — many facilities have no data recorded.
        </p>
      </div>

      <div className="flex items-center justify-between gap-3">
        <label
          htmlFor="limit"
          className="text-[11px] font-semibold uppercase tracking-wider text-slate-400"
        >
          Max results
        </label>
        <select
          id="limit"
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded-lg border border-slate-700/80 bg-slate-950/60 px-2.5 py-1.5 text-xs font-medium text-slate-200 outline-none transition hover:border-slate-600 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30"
        >
          {[50, 100, 150, 200].map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
