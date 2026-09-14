import { useEffect, useMemo, useState } from "react";
import { CitySelect } from "./components/CitySelect.jsx";
import { Filters } from "./components/Filters.jsx";
import { FacilityList } from "./components/FacilityList.jsx";
import { MapView } from "./components/MapView.jsx";
import { fetchFacilities } from "./api/client.js";

const DEFAULT_LIMIT = 150;

function Stat({ label, value, accent }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 px-2 py-1.5 text-center">
      <div className={`text-base font-semibold leading-none ${accent}`}>{value}</div>
      <div className="mt-1 text-[10px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
    </div>
  );
}

export default function App() {
  const [city, setCity] = useState("");
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [ownership, setOwnership] = useState("");
  const [emergencyOnly, setEmergencyOnly] = useState(false);
  const [open24, setOpen24] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    if (!city) {
      setFacilities([]);
      setError("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");
    setSelectedId(null);

    fetchFacilities({ city, limit })
      .then((data) => {
        if (!cancelled) setFacilities(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!cancelled) {
          console.error(err);
          setError(
            err?.response?.data?.detail ||
              "Could not load facilities. Check that the Django backend is running."
          );
          setFacilities([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [city, limit]);

  const filteredFacilities = useMemo(
    () =>
      facilities.filter((f) => {
        if (ownership && f.ownership !== ownership) return false;
        if (emergencyOnly && !f.is_emergency) return false;
        if (open24 && !f.is_24_7) return false;
        return true;
      }),
    [facilities, ownership, emergencyOnly, open24]
  );

  const stats = useMemo(() => {
    const counts = { total: filteredFacilities.length, hospitals: 0, emergency: 0 };
    for (const f of filteredFacilities) {
      if (f.facility_type === "Hospital") counts.hospitals += 1;
      if (f.is_emergency) counts.emergency += 1;
    }
    return counts;
  }, [filteredFacilities]);

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 md:h-screen md:overflow-hidden">
      <header className="shrink-0 border-b border-slate-800/80 bg-slate-950/80 px-4 py-3 backdrop-blur md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/15 text-base ring-1 ring-brand-500/30">
              🏥
            </span>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-slate-50 md:text-base">
                Accessible KPK
              </h1>
              <p className="text-[11px] text-slate-400">
                Healthcare facility finder · Khyber Pakhtunkhwa
              </p>
            </div>
          </div>
          <span className="rounded-full border border-slate-700/70 bg-slate-900/70 px-2.5 py-1 text-[10px] font-medium text-slate-400">
            Live data · OpenStreetMap
          </span>
        </div>
      </header>

      <main className="grid flex-1 gap-3 p-3 md:min-h-0 md:grid-cols-[340px_minmax(0,1fr)] md:gap-4 md:p-4">
        <aside className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-3 md:min-h-0 md:overflow-hidden">
          <div className="shrink-0 space-y-3">
            <CitySelect value={city} onChange={setCity} />
            <Filters
              ownership={ownership}
              setOwnership={setOwnership}
              emergencyOnly={emergencyOnly}
              setEmergencyOnly={setEmergencyOnly}
              open24={open24}
              setOpen24={setOpen24}
              limit={limit}
              setLimit={setLimit}
            />

            {city && !loading && !error && facilities.length > 0 && (
              <div className="grid grid-cols-3 gap-1.5">
                <Stat label="Results" value={stats.total} accent="text-slate-100" />
                <Stat label="Hospitals" value={stats.hospitals} accent="text-rose-300" />
                <Stat label="Emergency" value={stats.emergency} accent="text-amber-300" />
              </div>
            )}

            <div className="h-px bg-slate-800" />
          </div>

          <div className="flex min-w-0 flex-col md:min-h-0 md:flex-1 md:overflow-y-auto md:pr-0.5">
            <FacilityList
              facilities={filteredFacilities}
              loading={loading}
              error={error}
              selectedCity={city}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
        </aside>

        <section className="h-[55vh] min-w-0 md:h-auto md:min-h-0">
          <MapView
            facilities={filteredFacilities}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </section>
      </main>
    </div>
  );
}
