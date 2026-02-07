function OwnershipBadge({ ownership }) {
  if (!ownership) return null;
  const isGov = ownership === "government";
  const color = isGov ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/40" : "bg-sky-500/10 text-sky-300 border-sky-500/40";
  const label = isGov ? "Government" : "Private";

  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${color}`}>
      {label}
    </span>
  );
}

function Tag({ children }) {
  return (
    <span className="inline-flex items-center rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-200">
      {children}
    </span>
  );
}

export function FacilityList({ facilities, loading, error, selectedCity }) {
  if (!selectedCity) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
        Select a city in KPK to explore nearby healthcare facilities.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-slate-800 bg-slate-950/50 p-6 text-sm text-slate-300">
        Fetching live data from OpenStreetMap for {selectedCity}…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/40 bg-red-950/40 p-4 text-sm text-red-100">
        <p className="font-semibold">Unable to load facilities.</p>
        <p className="mt-1 text-xs opacity-80">
          {error || "There was a problem communicating with the backend or Overpass API."}
        </p>
      </div>
    );
  }

  if (!facilities || facilities.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-slate-800 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
        No healthcare facilities were found in OpenStreetMap for {selectedCity}. Data coverage may be incomplete.
      </div>
    );
  }

  return (
    <div className="space-y-2 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>
          Showing <span className="font-semibold text-slate-200">{facilities.length}</span> facilities in{" "}
          <span className="font-semibold text-slate-200">{selectedCity}</span>
        </span>
        <span>Source: OpenStreetMap (via Overpass API)</span>
      </div>
      <ul className="mt-1 space-y-2">
        {facilities.map((f) => (
          <li
            key={f.osm_id}
            className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 text-xs hover:border-brand-500/60 hover:bg-slate-900"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">
                  {f.name || "Unnamed facility"}
                </h3>
                <p className="mt-0.5 text-[11px] text-slate-400">{f.address || "Address not available"}</p>
              </div>
              <div className="flex flex-col items-end gap-1">
                {f.facility_type && <Tag>{f.facility_type}</Tag>}
                <OwnershipBadge ownership={f.ownership} />
              </div>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              {f.phone && <Tag>Phone: {f.phone}</Tag>}
              {f.is_emergency && <Tag>Emergency</Tag>}
              {f.is_24_7 && <Tag>24/7</Tag>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

