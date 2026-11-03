import { useEffect, useMemo, useState } from "react";
import { CitySelect } from "./components/CitySelect.jsx";
import { Filters } from "./components/Filters.jsx";
import { LocationControl } from "./components/LocationControl.jsx";
import { SearchBox } from "./components/SearchBox.jsx";
import { FacilityList } from "./components/FacilityList.jsx";
import { MapView } from "./components/MapView.jsx";
import { Pagination } from "./components/Pagination.jsx";
import { fetchFacilities } from "./api/client.js";
import { describeGeolocationError, getCurrentCoordinates } from "./lib/geolocation.js";
import { useDebouncedValue } from "./lib/useDebouncedValue.js";

const DEFAULT_LIMIT = 150;
const PAGE_SIZE = 20;

const DEFAULT_FILTERS = {
  ownership: "",
  emergency: false,
  open24: false,
  wheelchair: false,
  type: "",
  sort: "",
};

const VIEWS = [
  { value: "split", label: "List and map" },
  { value: "list", label: "List" },
  { value: "map", label: "Map" },
];

export default function App() {
  const [city, setCity] = useState("");
  const [coords, setCoords] = useState(null); // { lat, lon } once the visitor shares their location
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");

  const [searchText, setSearchText] = useState("");
  const query = useDebouncedValue(searchText.trim(), 300);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [filtersOpen, setFiltersOpen] = useState(false); // only matters on small screens

  const [facilities, setFacilities] = useState([]);
  // Matches on the server (can exceed facilities.length) and whether the area
  // hit the backend's fetch cap.
  const [total, setTotal] = useState(0);
  const [capped, setCapped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [view, setView] = useState("split");

  const hasSearch = Boolean(city) || Boolean(coords);
  const setFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  const activeFilterCount = Object.entries(filters).filter(
    ([key, value]) => key !== "sort" && Boolean(value)
  ).length;

  async function locateMe() {
    setLocating(true);
    setLocationError("");
    try {
      setCoords(await getCurrentCoordinates());
    } catch (err) {
      setLocationError(describeGeolocationError(err));
    } finally {
      setLocating(false);
    }
  }

  useEffect(() => {
    if (!city && !coords) {
      setFacilities([]);
      setTotal(0);
      setCapped(false);
      setError("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");
    setSelectedId(null);

    // Filters, search and sorting are applied by the backend, before the limit.
    fetchFacilities({
      city,
      coords,
      limit,
      ownership: filters.ownership,
      emergency: filters.emergency,
      open24: filters.open24,
      wheelchair: filters.wheelchair,
      type: filters.type,
      sort: filters.sort,
      query,
    })
      .then((result) => {
        if (!cancelled) {
          setFacilities(result.facilities);
          setTotal(result.total);
          setCapped(result.capped);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error(err);
          setError(
            err?.response?.data?.detail ||
              "Could not load facilities. Check that the Django backend is running."
          );
          setFacilities([]);
          setTotal(0);
          setCapped(false);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [city, coords, limit, filters, query]);

  // Any change to the result set should send the reader back to page 1.
  useEffect(() => {
    setPage(1);
  }, [city, coords, filters, query, limit]);

  const totalPages = Math.max(1, Math.ceil(facilities.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () => facilities.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [facilities, currentPage]
  );

  // Tell the reader when the list is not the whole story.
  const truncationNotice = (() => {
    if (total > facilities.length) {
      return `Showing the first ${facilities.length} of ${total} matches. Choose a higher number under "Show up to" to see more.`;
    }
    if (capped) {
      return "This area reached the 500-facility limit, so more facilities may exist in OpenStreetMap.";
    }
    return "";
  })();

  const showList = view !== "map";
  const showMap = view !== "list";
  const hasResults = hasSearch && !loading && !error && facilities.length > 0;

  // Where `distance_km` is measured from, for the cards.
  const distanceFrom = coords ? "from you" : `from the centre of ${city}`;
  const heading = city ? `Facilities in ${city}` : coords ? "Facilities near you" : "Facilities";

  const gridCols =
    view === "split" ? "lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]" : "lg:grid-cols-1";

  return (
    <div className="flex min-h-screen flex-col bg-paper lg:h-screen lg:overflow-hidden">
      <a
        href="#results"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-[1000] focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:font-bold focus:text-brand"
      >
        Skip to results
      </a>

      <header className="shrink-0 border-b border-line bg-surface px-4 py-3 md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold leading-tight text-brand">Accessible KPK</h1>
            <p className="text-base text-ink-soft">
              Find hospitals, clinics and health units in Khyber Pakhtunkhwa
            </p>
          </div>

          <div
            role="group"
            aria-label="Layout"
            className="flex overflow-hidden rounded-md border-2 border-ink"
          >
            {VIEWS.map((v) => (
              <button
                key={v.value}
                type="button"
                onClick={() => setView(v.value)}
                aria-pressed={view === v.value}
                className={`px-4 py-2 text-base font-bold ${
                  view === v.value
                    ? "bg-brand text-white"
                    : "bg-surface text-ink hover:bg-brand-tint"
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="flex min-w-0 flex-1 flex-col gap-4 p-4 lg:min-h-0 lg:flex-row">
        <aside
          aria-label="Search and filters"
          className="flex w-full shrink-0 flex-col gap-5 rounded-lg border border-line bg-surface p-4 lg:w-[300px] lg:overflow-y-auto"
        >
          <CitySelect value={city} onChange={setCity} />
          <LocationControl
            active={Boolean(coords)}
            locating={locating}
            error={locationError}
            onLocate={locateMe}
            onClear={() => setCoords(null)}
          />
          <SearchBox value={searchText} onChange={setSearchText} />

          {/* On small screens the filters fold away so results are not pushed off-screen. */}
          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            aria-expanded={filtersOpen}
            aria-controls="filters"
            className="rounded-md border-2 border-ink bg-surface px-3 py-2.5 text-left text-base font-bold hover:bg-brand-tint lg:hidden"
          >
            {filtersOpen ? "Hide filters" : "Show filters"}
            {activeFilterCount > 0 && ` (${activeFilterCount} active)`}
          </button>
          <div id="filters" className={filtersOpen ? "block" : "hidden lg:block"}>
            <Filters
              filters={filters}
              setFilter={setFilter}
              limit={limit}
              setLimit={setLimit}
              activeCount={activeFilterCount}
              onReset={() => setFilters(DEFAULT_FILTERS)}
            />
          </div>
        </aside>

        <main className={`grid min-w-0 flex-1 gap-4 lg:min-h-0 ${gridCols}`}>
          {showList && (
            <section
              id="results"
              aria-label="Results"
              className="flex min-w-0 flex-col gap-3 lg:min-h-0"
            >
              <div className="shrink-0">
                <h2 className="text-xl font-bold">{heading}</h2>
                {hasResults && (
                  <p role="status" className="text-base text-ink-soft">
                    {total} {total === 1 ? "facility" : "facilities"} found
                  </p>
                )}
              </div>

              {hasResults && truncationNotice && (
                <p className="shrink-0 border-l-4 border-amber-600 bg-amber-50 px-3 py-2 text-base">
                  {truncationNotice}
                </p>
              )}

              <div className="min-w-0 flex-1 lg:min-h-0 lg:overflow-y-auto lg:pr-1">
                <FacilityList
                  facilities={pageItems}
                  loading={loading}
                  error={error}
                  hasSearch={hasSearch}
                  searchedText={query}
                  distanceFrom={distanceFrom}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  columns={view === "list" ? 3 : 1}
                />
              </div>

              {hasResults && (
                <Pagination
                  page={currentPage}
                  totalPages={totalPages}
                  total={facilities.length}
                  pageSize={PAGE_SIZE}
                  onPage={(p) => setPage(Math.min(Math.max(1, p), totalPages))}
                />
              )}
            </section>
          )}

          {showMap && (
            <section aria-label="Map" className="h-[55vh] min-w-0 lg:h-auto lg:min-h-0">
              <MapView
                facilities={pageItems}
                selectedId={selectedId}
                onSelect={setSelectedId}
                userLocation={coords}
              />
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
