// OSM contact values are free text and frequently malformed
// (e.g. "smile again hospital/facebook.com"), so validate before linking.
export function normalizeUrl(raw) {
  const value = String(raw || "").trim();
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  if (!/^[\w-]+(\.[\w-]+)+(\/.*)?$/.test(value)) return "";
  return `https://${value}`;
}

export function telHref(phone) {
  const cleaned = String(phone || "").replace(/[^\d+]/g, "");
  return cleaned ? `tel:${cleaned}` : "";
}

export function directionsUrl(lat, lon) {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
}
