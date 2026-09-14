import axios from "axios";

const baseURL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  // Longer than the backend's own 30s Overpass timeout, so we don't
  // give up client-side right before the backend would have responded.
  timeout: 35000,
});

export async function fetchFacilities({ city, limit = 100 }) {
  const params = new URLSearchParams();
  params.append("city", city);
  if (limit) {
    params.append("limit", String(limit));
  }

  const response = await api.get(`/api/facilities?${params.toString()}`);
  return response.data;
}

