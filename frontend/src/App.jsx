import { useEffect, useMemo, useState } from "react";
import { CitySelect } from "./components/CitySelect.jsx";
import { Filters } from "./components/Filters.jsx";
import { FacilityList } from "./components/FacilityList.jsx";
import { MapView } from "./components/MapView.jsx";
import { fetchFacilities } from "./api/client.js";

const DEFAULT_LIMIT = 150;

export default function App() {
  const [city, setCity] = useState("");
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [ownership, setOwnership] = useState("");
  const [emergencyOnly, setEmergencyOnly] = useState(false);
  const [open24, setOpen24] = useState(false);

  useEffect(() => {
    if (!city) {
      setFacilities([]);
      setError("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");

    fetchFacilities({ city, limit })
      .then((data) => {
        if (!cancelled) {
          setFacilities(Array.isArray(data) ? data : []);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error(err);
          setError(
            err?.response?.data?.detail ||
              "Could not load facilities. Please check that the Django backend is running."
          );
          setFacilities([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [city, limit]);

  const filteredFacilities = useMemo(() => {
    return facilities.filter((f) => {
      if (ownership && f.ownership !== ownership) return false;
      if (emergencyOnly && !f.is_emergency) return false;
      if (open24 && !f.is_24_7) return false;
      return true;
    });
  }, [facilities, ownership, emergencyOnly, open24]);

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 px-4 py-4 md:px-6 md:py-6">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold tracking-tight text-slate-50 md:text-2xl">
          Accessible KPK – Healthcare Facility Finder
        </h1>
        <p className="max-w-3xl text-xs text-slate-300 md:text-sm">
          A lightweight discovery tool for hospitals, clinics, Basic Health Units (BHUs) and Rural Health
          Centers (RHCs) across Khyber Pakhtunkhwa (KPK), Pakistan. Data is sourced from{" "}
          <span className="font-semibold text-slate-100">OpenStreetMap</span> and filtered for healthcare
          facilities only.
        </p>
      </header>

      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-xl shadow-black/40 md:grid-cols-[minmax(0,3fr)_minmax(0,4fr)] md:gap-5 md:p-5">
        <div className="flex flex-col gap-4">
          <CitySelect value={city} onChange={setCity} />

          <div className="flex flex-col gap-2 text-xs text-slate-300 md:flex-row md:items-center md:justify-between">
            <Filters
              ownership={ownership}
              setOwnership={setOwnership}
              emergencyOnly={emergencyOnly}
              setEmergencyOnly={setEmergencyOnly}
              open24={open24}
              setOpen24={setOpen24}
            />

            <div className="flex items-center gap-2 md:self-start">
              <label className="text-xs text-slate-300" htmlFor="limit">
                Max results
              </label>
              <select
                id="limit"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-100 shadow-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                {[50, 100, 150, 200].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <FacilityList
            facilities={filteredFacilities}
            loading={loading}
            error={error}
            selectedCity={city}
          />
        </div>

        <MapView facilities={filteredFacilities} />
      </section>

      <footer className="mt-auto border-t border-slate-800 pt-3 text-[11px] text-slate-500">
        <p>
          This is a semester project demo. Coverage depends on what is mapped in OpenStreetMap and may be
          incomplete or outdated. Always verify information directly with facilities.
        </p>
      </footer>
    </div>
  );
}

