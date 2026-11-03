import { TypeMark } from "./TypeMark.jsx";
import { facilityTitle } from "../lib/facilityName.js";
import { directionsUrl, normalizeUrl, telHref } from "../lib/contact.js";

const OWNERSHIP_LABELS = { government: "Government", private: "Private" };

// Wheelchair access, from the OpenStreetMap `wheelchair` tag. Unknown shows nothing.
const WHEELCHAIR_STATUS = {
  yes: { text: "Wheelchair accessible", className: "text-brand" },
  limited: { text: "Limited wheelchair access", className: "text-ink" },
  no: { text: "Not wheelchair accessible", className: "text-alert" },
};

const LINK = "font-bold text-brand underline underline-offset-2 hover:text-brand-dark";

function ContactRow({ facility, isSelected, onSelect }) {
  const tel = telHref(facility.phone);
  const site = normalizeUrl(facility.website);

  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line pt-3 text-base">
      {tel ? (
        <a href={tel} className={LINK}>
          Call {facility.phone}
        </a>
      ) : (
        <span className="text-ink-soft">No phone listed</span>
      )}
      <a
        href={directionsUrl(facility.lat, facility.lon)}
        target="_blank"
        rel="noopener noreferrer"
        className={LINK}
      >
        Directions
      </a>
      {site && (
        <a href={site} target="_blank" rel="noopener noreferrer" className={LINK}>
          Website
        </a>
      )}
      {facility.email && (
        <a href={`mailto:${facility.email}`} className={LINK}>
          Email
        </a>
      )}
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={isSelected}
        className={`${LINK} ml-auto`}
      >
        {isSelected ? "Selected on map" : "Show on map"}
      </button>
    </div>
  );
}

function Message({ title, hint, alert = false }) {
  return (
    <div
      role={alert ? "alert" : undefined}
      className={`rounded-lg border-2 border-dashed p-6 ${
        alert ? "border-alert text-alert" : "border-line text-ink"
      }`}
    >
      <p className="text-lg font-bold">{title}</p>
      {hint && <p className="mt-1 text-base">{hint}</p>}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading facilities">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="animate-pulse rounded-lg border border-line bg-surface p-4"
        >
          <div className="mb-3 h-4 w-2/3 rounded bg-line" />
          <div className="h-3 w-1/3 rounded bg-line" />
        </div>
      ))}
    </div>
  );
}

export function FacilityList({
  facilities,
  loading,
  error,
  hasSearch,
  searchedText = "",
  distanceFrom = "",
  selectedId,
  onSelect,
  columns = 1,
}) {
  if (!hasSearch) {
    return (
      <Message
        title="Choose a city or use your location"
        hint="Pick a city or town, or share your location, to see hospitals, clinics and health units nearby."
      />
    );
  }

  if (loading) return <Skeleton />;

  if (error) {
    // A visitor outside KPK is not a failure; say so plainly. (The API's message
    // for this case contains "outside the supported".)
    if (error.includes("outside the supported")) {
      return (
        <Message
          title="Your location is outside Khyber Pakhtunkhwa"
          hint="This site only covers Khyber Pakhtunkhwa. Choose a city instead, or stop using your location."
        />
      );
    }
    return <Message alert title="We couldn't load the facilities" hint={error} />;
  }

  if (!facilities.length) {
    return (
      <Message
        title={searchedText ? `Nothing found for "${searchedText}"` : "Nothing found"}
        hint="Try a different search or remove a filter. OpenStreetMap may not have every facility here."
      />
    );
  }

  return (
    <ul
      className={
        columns > 1 ? "grid gap-3 sm:grid-cols-2 xl:grid-cols-3" : "space-y-3"
      }
    >
      {facilities.map((f) => {
        const isSelected = selectedId === f.osm_id;
        const details = [f.facility_type, OWNERSHIP_LABELS[f.ownership]].filter(Boolean);
        const wheelchair = WHEELCHAIR_STATUS[f.wheelchair];
        return (
          <li key={f.osm_id}>
            <article
              onClick={() => onSelect(isSelected ? null : f.osm_id)}
              className={`h-full cursor-pointer rounded-lg border bg-surface p-4 ${
                isSelected
                  ? "border-brand ring-2 ring-brand"
                  : "border-line hover:border-ink-soft"
              }`}
            >
              <div className="flex gap-3">
                <TypeMark type={f.facility_type} />
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-bold leading-snug">{facilityTitle(f)}</h3>
                  {details.length > 0 && (
                    <p className="text-base text-ink-soft">{details.join(" · ")}</p>
                  )}
                  {f.address && <p className="mt-1 text-base">{f.address}</p>}
                  {f.distance_km != null && (
                    <p className="mt-1 text-base">
                      <strong>{f.distance_km} km</strong> {distanceFrom}
                    </p>
                  )}
                  {(f.is_emergency || f.is_24_7 || wheelchair) && (
                    <ul className="mt-2 space-y-0.5 text-base font-bold">
                      {f.is_emergency && <li className="text-alert">Emergency services</li>}
                      {f.is_24_7 && <li className="text-brand">Open 24 hours</li>}
                      {wheelchair && <li className={wheelchair.className}>{wheelchair.text}</li>}
                    </ul>
                  )}
                  <div onClick={(e) => e.stopPropagation()}>
                    <ContactRow
                      facility={f}
                      isSelected={isSelected}
                      onSelect={() => onSelect(isSelected ? null : f.osm_id)}
                    />
                  </div>
                </div>
              </div>
            </article>
          </li>
        );
      })}
    </ul>
  );
}
