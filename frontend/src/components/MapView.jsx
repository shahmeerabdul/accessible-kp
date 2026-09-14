import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { styleForType } from "../lib/facilityStyle.js";
import { directionsUrl, telHref } from "../lib/contact.js";

const DEFAULT_CENTER = [34.0151, 71.5249]; // Roughly Peshawar / central KPK

function pinIcon(hex, selected) {
  const size = selected ? 34 : 26;
  return L.divIcon({
    className: "",
    html: `<div style="
        width:${size}px;height:${size}px;
        border-radius:50% 50% 50% 0;
        background:${hex};
        transform:rotate(-45deg);
        border:2px solid rgba(255,255,255,.85);
        box-shadow:0 2px 8px rgba(0,0,0,.5)${selected ? `,0 0 0 6px ${hex}33` : ""};
      "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size + 4],
  });
}

/** Keep Leaflet in sync when its container is resized (e.g. the view toggle). */
function ResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(container);
    return () => observer.disconnect();
  }, [map]);

  return null;
}

/** Fit the map to the current results, and fly to a facility when selected. */
function MapController({ facilities, selected }) {
  const map = useMap();
  const lastFitKey = useRef("");

  useEffect(() => {
    if (selected) {
      map.flyTo([selected.lat, selected.lon], Math.max(map.getZoom(), 15), {
        duration: 0.8,
      });
    }
  }, [map, selected]);

  useEffect(() => {
    if (selected || !facilities.length) return;
    // Only refit when the result set itself changes, not on every render.
    const key = facilities.map((f) => f.osm_id).join(",");
    if (key === lastFitKey.current) return;
    lastFitKey.current = key;

    const bounds = L.latLngBounds(facilities.map((f) => [f.lat, f.lon]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }, [map, facilities, selected]);

  return null;
}

export function MapView({ facilities, selectedId, onSelect }) {
  const selected = useMemo(
    () => facilities.find((f) => f.osm_id === selectedId) || null,
    [facilities, selectedId]
  );

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={12}
        scrollWheelZoom
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ResizeHandler />
        <MapController facilities={facilities} selected={selected} />

        {facilities.map((f) => {
          const style = styleForType(f.facility_type);
          const isSelected = f.osm_id === selectedId;
          return (
            <Marker
              key={f.osm_id}
              position={[f.lat, f.lon]}
              icon={pinIcon(style.hex, isSelected)}
              zIndexOffset={isSelected ? 1000 : 0}
              eventHandlers={{ click: () => onSelect(f.osm_id) }}
            >
              <Popup>
                <div className="space-y-1 text-xs">
                  <div className="text-sm font-semibold">
                    {f.name || "Unnamed facility"}
                  </div>
                  {f.facility_type && (
                    <div className="font-medium" style={{ color: style.hex }}>
                      {f.facility_type}
                    </div>
                  )}
                  {f.address && <div>{f.address}</div>}
                  {f.phone ? (
                    <div>
                      📞{" "}
                      <a href={telHref(f.phone)} className="font-semibold">
                        {f.phone}
                      </a>
                    </div>
                  ) : (
                    <div className="opacity-60">No phone in OpenStreetMap</div>
                  )}
                  <div>
                    <a
                      href={directionsUrl(f.lat, f.lon)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Directions →
                    </a>
                  </div>
                  <div className="flex flex-wrap gap-1 pt-0.5">
                    {f.is_emergency && (
                      <span className="rounded bg-red-100 px-1 py-0.5 text-[10px] font-semibold text-red-700">
                        Emergency
                      </span>
                    )}
                    {f.is_24_7 && (
                      <span className="rounded bg-teal-100 px-1 py-0.5 text-[10px] font-semibold text-teal-700">
                        24/7
                      </span>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {facilities.length > 0 && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[400] flex flex-wrap gap-2 rounded-lg border border-slate-700/70 bg-slate-950/85 px-2.5 py-2 backdrop-blur">
          {["Hospital", "Clinic", "BHU", "RHC"].map((t) => (
            <span
              key={t}
              className="flex items-center gap-1.5 text-[10px] font-medium text-slate-300"
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: styleForType(t).hex }}
              />
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
