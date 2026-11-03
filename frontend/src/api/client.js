import axios from "axios";

const baseURL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  // Longer than the backend's own 30s Overpass timeout, so we don't
  // give up client-side right before the backend would have responded.
  timeout: 35000,
});

/**
 * Search facilities by city and/or by the visitor's location.
 *
 * Filters, text search and sorting are done by the backend before the limit,
 * so they cover every facility fetched for the area, not just the first `limit`.
 *
 * Resolves to { facilities, total, capped }:
 *  - total:  how many facilities match (may exceed facilities.length)
 *  - capped: the area hit the backend's fetch cap, so more may exist upstream
 */
export async function fetchFacilities({
  city = "",
  coords = null,
  limit = 100,
  ownership = "",
  emergency = false,
  open24 = false,
  wheelchair = false,
  type = "",
  sort = "",
  query = "",
}) {
  const params = new URLSearchParams();
  if (city) params.append("city", city);
  if (coords) {
    params.append("lat", String(coords.lat));
    params.append("lon", String(coords.lon));
  }
  if (limit) params.append("limit", String(limit));
  if (ownership) params.append("ownership", ownership);
  if (emergency) params.append("emergency", "true");
  if (open24) params.append("open_24_7", "true");
  if (wheelchair) params.append("wheelchair", "true");
  if (type) params.append("type", type);
  if (sort) params.append("sort", sort);
  if (query) params.append("q", query);

  const response = await api.get(`/api/facilities?${params.toString()}`);
  const facilities = Array.isArray(response.data) ? response.data : [];
  const total = Number(response.headers["x-total-count"]);

  return {
    facilities,
    total: Number.isFinite(total) ? total : facilities.length,
    capped: response.headers["x-upstream-capped"] === "true",
  };
}
