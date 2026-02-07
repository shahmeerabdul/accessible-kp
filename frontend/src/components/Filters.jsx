const ownershipOptions = [
  { value: "", label: "All ownership types" },
  { value: "government", label: "Government" },
  { value: "private", label: "Private" },
];

export function Filters({ ownership, setOwnership, emergencyOnly, setEmergencyOnly, open24, setOpen24 }) {
  return (
    <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-sm md:grid-cols-3">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-slate-300">Ownership</label>
        <select
          value={ownership}
          onChange={(e) => setOwnership(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-100 shadow-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        >
          {ownershipOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <label className="flex items-center gap-2 text-xs text-slate-200">
        <input
          type="checkbox"
          checked={!!emergencyOnly}
          onChange={(e) => setEmergencyOnly(e.target.checked)}
          className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-brand-500 focus:ring-brand-500"
        />
        Emergency services available (where known)
      </label>

      <label className="flex items-center gap-2 text-xs text-slate-200">
        <input
          type="checkbox"
          checked={!!open24}
          onChange={(e) => setOpen24(e.target.checked)}
          className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-brand-500 focus:ring-brand-500"
        />
        24/7 facilities only (where known)
      </label>
    </div>
  );
}

