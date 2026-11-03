import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { styleForType } from "../lib/facilityStyle.js";
import { facilityTitle } from "../lib/facilityName.js";
import { TypeMark } from "./TypeMark.jsx";
import { directionsUrl, telHref } from "../lib/contact.js";

const DEFAULT_CENTER = [34.0151, 71.5249]; // Roughly Peshawar / central KPK

// Pin = round marker with the facility-type letter, so type isn't shown by colour alone.
// `letter` always comes from styleForType, which only ever returns a single plain character.
function pinIcon({ hex, letter }, selected) {
  const size = selected ? 38 : 30;
  return L.divIcon({
    className: "",
    html: `<div style="
        width:${size}px;height:${size}px;
        display:flex;align-items:center;justify-content:center;
        border-radius:50%;
        background:${hex};color:#fff;
        font:700 ${selected ? 17 : 14}px/1 'Atkinson Hyperlegible',system-ui,sans-serif;
        border:3px solid #fff;
        box-shadow:0 1px 4px rgba(0,0,0,.5)${selected ? ",0 0 0 3px #1C2024" : ""};
      ">${letter}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
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
function MapController({ facilities, selected, userLocation }) {
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
    const key =
      facilities.map((f) => f.osm_id).join(",") +
      (userLocation ? `|${userLocation.lat},${userLocation.lon}` : "");
    if (key === lastFitKey.current) return;
    lastFitKey.current = key;

    // Include the visitor's own position so "near me" results are shown around them.
    const points = facilities.map((f) => [f.lat, f.lon]);
    if (userLocation) points.push([userLocation.lat, userLocation.lon]);
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 14 });
  }, [map, facilities, selected, userLocation]);

  return null;
}

const WHEELCHAIR_TEXT = {
  yes: "Wheelchair accessible",
  limited: "Limited wheelchair access",
  no: "Not wheelchair accessible",
};

export function MapView({ facilities, selectedId, onSelect, userLocation = null }) {
  const selected = useMemo(
    () => facilities.find((f) => f.osm_id === selectedId) || null,
    [facilities, selectedId]
  );

  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg border border-line bg-surface">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={12}
        scrollWheelZoom
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="muted-tiles"
        />
        <ResizeHandler />
        <MapController facilities={facilities} selected={selected} userLocation={userLocation} />

        {userLocation && (
          <CircleMarker
            center={[userLocation.lat, userLocation.lon]}
            radius={9}
            pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#1d4e89", fillOpacity: 1 }}
          >
            <Tooltip permanent direction="top" offset={[0, -8]}>
              You are here
            </Tooltip>
          </CircleMarker>
        )}

        {facilities.map((f) => {
          const style = styleForType(f.facility_type);
          const isSelected = f.osm_id === selectedId;
          return (
            <Marker
              key={f.osm_id}
              position={[f.lat, f.lon]}
              icon={pinIcon(style, isSelected)}
              zIndexOffset={isSelected ? 1000 : 0}
              eventHandlers={{ click: () => onSelect(f.osm_id) }}
            >
              <Popup>
                <div className="space-y-1">
                  <div className="text-base font-bold">{facilityTitle(f)}</div>
                  {f.facility_type && <div className="text-ink-soft">{f.facility_type}</div>}
                  {f.address && <div>{f.address}</div>}
                  {f.phone ? (
                    <div>
                      <a href={telHref(f.phone)}>Call {f.phone}</a>
                    </div>
                  ) : (
                    <div className="text-ink-soft">No phone listed</div>
                  )}
                  <div>
                    <a
                      href={directionsUrl(f.lat, f.lon)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Directions
                    </a>
                  </div>
                  {(f.is_emergency || f.is_24_7 || WHEELCHAIR_TEXT[f.wheelchair]) && (
                    <div className="font-bold">
                      {f.is_emergency && <div className="text-alert">Emergency services</div>}
                      {f.is_24_7 && <div className="text-brand">Open 24 hours</div>}
                      {WHEELCHAIR_TEXT[f.wheelchair] && <div>{WHEELCHAIR_TEXT[f.wheelchair]}</div>}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {facilities.length > 0 && (
        <div
          role="group"
          aria-label="Map key"
          className="absolute bottom-6 left-3 z-[400] flex flex-wrap gap-x-4 gap-y-2 rounded-lg border border-line bg-surface px-3 py-2 shadow"
        >
          {["Hospital", "Clinic", "BHU", "RHC"].map((t) => (
            <span key={t} className="flex items-center gap-2 text-sm font-bold">
              <TypeMark type={t} />
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
