const TYPE_OPTIONS = [
  { value: "", label: "All types" },
  { value: "hospital", label: "Hospitals" },
  { value: "clinic", label: "Clinics" },
  { value: "health_unit", label: "Health units (BHU and RHC)" },
  { value: "pharmacy_lab", label: "Pharmacies and labs" },
  { value: "other", label: "Other" },
];

const SORT_OPTIONS = [
  { value: "", label: "Default order" },
  { value: "name", label: "Name (A to Z)" },
  { value: "distance", label: "Nearest first" },
];

const OWNERSHIP_OPTIONS = [
  { value: "", label: "All" },
  { value: "government", label: "Government" },
  { value: "private", label: "Private" },
];

const LIMIT_OPTIONS = [50, 100, 150, 200, 300, 500];

const SELECT_CLASS = "w-full rounded-md border-2 border-ink bg-surface px-3 py-2.5 text-base";

function Select({ id, label, value, onChange, children }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-base font-bold">
        {label}
      </label>
      <select id={id} value={value} onChange={onChange} className={SELECT_CLASS}>
        {children}
      </select>
    </div>
  );
}

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

export function Filters({ filters, setFilter, limit, setLimit, activeCount, onReset }) {
  return (
    <div className="flex flex-col gap-5">
      <Select
        id="type"
        label="Type of facility"
        value={filters.type}
        onChange={(e) => setFilter("type", e.target.value)}
      >
        {TYPE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>

      <Select
        id="sort"
        label="Sort by"
        value={filters.sort}
        onChange={(e) => setFilter("sort", e.target.value)}
      >
        {SORT_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>

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
              checked={filters.ownership === opt.value}
              onChange={() => setFilter("ownership", opt.value)}
              className="h-5 w-5 shrink-0 accent-brand"
            />
            {opt.label}
          </label>
        ))}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-base font-bold">Show only</legend>
        <Checkbox
          id="emergency"
          checked={filters.emergency}
          onChange={(v) => setFilter("emergency", v)}
        >
          Has emergency services
        </Checkbox>
        <Checkbox id="open24" checked={filters.open24} onChange={(v) => setFilter("open24", v)}>
          Open 24 hours
        </Checkbox>
        <Checkbox
          id="wheelchair"
          checked={filters.wheelchair}
          onChange={(v) => setFilter("wheelchair", v)}
        >
          Wheelchair accessible
        </Checkbox>
        <p className="text-sm text-ink-soft">
          Based on OpenStreetMap data. Many facilities have nothing recorded, so they will
          not match these filters. Wheelchair information is especially rare.
        </p>
      </fieldset>

      <Select
        id="limit"
        label="Show up to"
        value={limit}
        onChange={(e) => setLimit(Number(e.target.value))}
      >
        {LIMIT_OPTIONS.map((v) => (
          <option key={v} value={v}>
            {v} results
          </option>
        ))}
      </Select>

      {activeCount > 0 && (
        <button
          type="button"
          onClick={onReset}
          className="self-start text-base font-bold text-brand underline underline-offset-2 hover:text-brand-dark"
        >
          Clear all filters ({activeCount})
        </button>
      )}
    </div>
  );
}
