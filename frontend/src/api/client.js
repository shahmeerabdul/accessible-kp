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
 * Filters are applied by the backend before the limit, so they cover every
 * facility fetched for the city, not just the first `limit`.
 *
 * Resolves to { facilities, total, capped }:
 *  - total:  how many facilities match the filters (may exceed facilities.length)
 *  - capped: the city hit the backend's fetch cap, so more may exist upstream
 */
export async function fetchFacilities({
  city,
  limit = 100,
  ownership = "",
  emergency = false,
  open24 = false,
}) {
  const params = new URLSearchParams();
  params.append("city", city);
  if (limit) {
    params.append("limit", String(limit));
  }
  if (ownership) params.append("ownership", ownership);
  if (emergency) params.append("emergency", "true");
  if (open24) params.append("open_24_7", "true");

  const response = await api.get(`/api/facilities?${params.toString()}`);
  const facilities = Array.isArray(response.data) ? response.data : [];
  const total = Number(response.headers["x-total-count"]);

  return {
    facilities,
    total: Number.isFinite(total) ? total : facilities.length,
    capped: response.headers["x-upstream-capped"] === "true",
  };
}

