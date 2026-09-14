import { KPK_CITIES } from "../constants/cities.js";

export function CitySelect({ value, onChange }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor="city"
        className="text-[11px] font-semibold uppercase tracking-wider text-slate-400"
      >
        City / Town
      </label>
      <div className="relative">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="M12 21s-7-5.6-7-11a7 7 0 1 1 14 0c0 5.4-7 11-7 11Z" />
          <circle cx="12" cy="10" r="2.5" />
        </svg>
        <select
          id="city"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none rounded-lg border border-slate-700/80 bg-slate-950/80 py-2.5 pl-9 pr-9 text-sm font-medium text-slate-100 shadow-sm outline-none transition hover:border-slate-600 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30"
        >
          <option value="">Select a city…</option>
          {KPK_CITIES.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </select>
        <svg
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>
    </div>
  );
}
