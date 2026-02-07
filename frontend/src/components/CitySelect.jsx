import { KPK_CITIES } from "../constants/cities.js";

export function CitySelect({ value, onChange }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="city" className="text-sm font-medium text-slate-200">
        City / Town in KPK
      </label>
      <select
        id="city"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 shadow-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
      >
        <option value="">Select a city</option>
        {KPK_CITIES.map((city) => (
          <option key={city} value={city}>
            {city}
          </option>
        ))}
      </select>
      <p className="text-xs text-slate-400">
        Data is fetched live from OpenStreetMap via the Overpass API.
      </p>
    </div>
  );
}

