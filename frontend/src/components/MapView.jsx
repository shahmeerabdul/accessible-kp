import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default icon paths when bundling with Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const DEFAULT_CENTER = [34.0151, 71.5249]; // Roughly Peshawar / central KPK

function Recenter({ center, zoom }) {
  const map = useMap();

  // MapContainer's `center`/`zoom` props only apply on first mount, so without
  // this the map would stay wherever it was when the user picks a new city.
  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center[0], center[1], zoom]);

  return null;
}

export function MapView({ facilities }) {
  const hasFacilities = facilities && facilities.length > 0;

  const first = hasFacilities ? [facilities[0].lat, facilities[0].lon] : DEFAULT_CENTER;

  return (
    <div className="h-80 w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950/80 md:h-full">
      <MapContainer
        center={first}
        zoom={12}
        scrollWheelZoom={true}
        className="h-full w-full"
      >
        <Recenter center={first} zoom={12} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {hasFacilities &&
          facilities.map((f) => (
            <Marker key={f.osm_id} position={[f.lat, f.lon]}>
              <Popup>
                <div className="space-y-1 text-xs">
                  <div className="font-semibold">{f.name || "Unnamed facility"}</div>
                  {f.facility_type && <div>{f.facility_type}</div>}
                  {f.address && <div className="text-slate-700">{f.address}</div>}
                  {f.phone && <div>Phone: {f.phone}</div>}
                  <div className="flex flex-wrap gap-1">
                    {f.is_emergency && <span className="rounded bg-red-100 px-1 py-0.5">Emergency</span>}
                    {f.is_24_7 && <span className="rounded bg-emerald-100 px-1 py-0.5">24/7</span>}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
      </MapContainer>
    </div>
  );
}

