import { KPK_CITIES } from "../constants/cities.js";

export function CitySelect({ value, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="city" className="text-base font-bold">
        City or town
      </label>
      <select
        id="city"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border-2 border-ink bg-surface px-3 py-2.5 text-base"
      >
        <option value="">Choose a city</option>
        {KPK_CITIES.map((city) => (
          <option key={city} value={city}>
            {city}
          </option>
        ))}
      </select>
    </div>
  );
}
