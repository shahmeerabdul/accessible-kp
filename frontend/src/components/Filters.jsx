const OWNERSHIP_OPTIONS = [
  { value: "", label: "All" },
  { value: "government", label: "Government" },
  { value: "private", label: "Private" },
];

const LIMIT_OPTIONS = [50, 100, 150, 200, 300, 500];

function Checkbox({ id, checked, onChange, children }) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-center gap-3 text-base">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-5 shrink-0 accent-brand"
      />
      {children}
    </label>
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
    <div className="flex flex-col gap-5">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-base font-bold">Ownership</legend>
        {OWNERSHIP_OPTIONS.map((opt) => (
          <label
            key={opt.value || "all"}
            className="flex cursor-pointer items-center gap-3 text-base"
          >
            <input
              type="radio"
              name="ownership"
              value={opt.value}
              checked={ownership === opt.value}
              onChange={() => setOwnership(opt.value)}
              className="h-5 w-5 shrink-0 accent-brand"
            />
            {opt.label}
          </label>
        ))}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-base font-bold">Show only</legend>
        <Checkbox id="emergency" checked={emergencyOnly} onChange={setEmergencyOnly}>
          Has emergency services
        </Checkbox>
        <Checkbox id="open24" checked={open24} onChange={setOpen24}>
          Open 24 hours
        </Checkbox>
        <p className="text-sm text-ink-soft">
          Based on OpenStreetMap data. Many facilities have nothing recorded, so they
          won't match these filters.
        </p>
      </fieldset>

      <div className="flex flex-col gap-2">
        <label htmlFor="limit" className="text-base font-bold">
          Show up to
        </label>
        <select
          id="limit"
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="w-full rounded-md border-2 border-ink bg-surface px-3 py-2.5 text-base"
        >
          {LIMIT_OPTIONS.map((v) => (
            <option key={v} value={v}>
              {v} results
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
