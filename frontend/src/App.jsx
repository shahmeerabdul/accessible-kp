import { useEffect, useMemo, useState } from "react";
import { CitySelect } from "./components/CitySelect.jsx";
import { Filters } from "./components/Filters.jsx";
import { FacilityList } from "./components/FacilityList.jsx";
import { MapView } from "./components/MapView.jsx";
import { Pagination } from "./components/Pagination.jsx";
import { fetchFacilities } from "./api/client.js";

const DEFAULT_LIMIT = 150;
const PAGE_SIZE = 20;

const VIEWS = [
  { value: "split", label: "Split" },
  { value: "list", label: "List" },
  { value: "map", label: "Map" },
];

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
  const [page, setPage] = useState(1);
  const [view, setView] = useState("split");

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

  // Any change to the result set should send the reader back to page 1.
  useEffect(() => {
    setPage(1);
  }, [city, ownership, emergencyOnly, open24, limit]);

  const totalPages = Math.max(1, Math.ceil(filteredFacilities.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () =>
      filteredFacilities.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [filteredFacilities, currentPage]
  );

  const stats = useMemo(() => {
    const counts = { total: filteredFacilities.length, hospitals: 0, emergency: 0 };
    for (const f of filteredFacilities) {
      if (f.facility_type === "Hospital") counts.hospitals += 1;
      if (f.is_emergency) counts.emergency += 1;
    }
    return counts;
  }, [filteredFacilities]);

  const showList = view !== "map";
  const showMap = view !== "list";
  const hasResults = Boolean(city) && !loading && !error && facilities.length > 0;

  const gridCols =
    view === "split" ? "lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]" : "lg:grid-cols-1";

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 lg:h-screen lg:overflow-hidden">
      <header className="shrink-0 border-b border-slate-800/80 bg-slate-950/80 px-4 py-2.5 backdrop-blur md:px-6">
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

          <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/70 p-0.5">
            {VIEWS.map((v) => (
              <button
                key={v.value}
                type="button"
                onClick={() => setView(v.value)}
                aria-pressed={view === v.value}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                  view === v.value
                    ? "bg-brand-500/20 text-brand-200 ring-1 ring-brand-500/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="flex min-w-0 flex-1 flex-col gap-3 p-3 lg:min-h-0 lg:flex-row lg:gap-4 lg:p-4">
        <aside className="flex w-full shrink-0 flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-3 lg:w-[290px] lg:overflow-y-auto">
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
          {hasResults && (
            <div className="grid grid-cols-3 gap-1.5">
              <Stat label="Results" value={stats.total} accent="text-slate-100" />
              <Stat label="Hospitals" value={stats.hospitals} accent="text-rose-300" />
              <Stat label="Emergency" value={stats.emergency} accent="text-amber-300" />
            </div>
          )}
        </aside>

        <main className={`grid min-w-0 flex-1 gap-3 lg:min-h-0 lg:gap-4 ${gridCols}`}>
          {showList && (
            <section className="flex min-w-0 flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/40 p-3 lg:min-h-0">
              <div className="flex shrink-0 items-baseline justify-between gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {city ? `Facilities in ${city}` : "Facilities"}
                </h2>
                {hasResults && (
                  <span className="text-[11px] text-slate-500">
                    Page {currentPage} of {totalPages}
                  </span>
                )}
              </div>

              <div className="min-w-0 flex-1 lg:min-h-0 lg:overflow-y-auto lg:pr-1">
                <FacilityList
                  facilities={pageItems}
                  loading={loading}
                  error={error}
                  selectedCity={city}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  columns={view === "list" ? 3 : 1}
                />
              </div>

              {hasResults && (
                <Pagination
                  page={currentPage}
                  totalPages={totalPages}
                  total={filteredFacilities.length}
                  pageSize={PAGE_SIZE}
                  onPage={(p) => setPage(Math.min(Math.max(1, p), totalPages))}
                />
              )}
            </section>
          )}

          {showMap && (
            <section className="h-[55vh] min-w-0 lg:h-auto lg:min-h-0">
              <MapView
                facilities={pageItems}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
