import { styleForType } from "../lib/facilityStyle.js";
import { directionsUrl, normalizeUrl, telHref } from "../lib/contact.js";

function Badge({ className, children }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${className}`}
    >
      {children}
    </span>
  );
}

function Icon({ path }) {
  return (
    <svg
      className="h-3.5 w-3.5 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {path}
    </svg>
  );
}

const PHONE_PATH = (
  <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 1.9.6 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.1a2 2 0 0 1 2.1-.5c.9.3 1.8.5 2.8.6a2 2 0 0 1 1.7 2Z" />
);

function ContactRow({ facility }) {
  const tel = telHref(facility.phone);
  const site = normalizeUrl(facility.website);
  const stop = (e) => e.stopPropagation();

  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-800/80 pt-1.5">
      {tel ? (
        <a
          href={tel}
          onClick={stop}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-300 hover:text-brand-200 hover:underline"
        >
          <Icon path={PHONE_PATH} />
          {facility.phone}
        </a>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-600">
          <Icon path={PHONE_PATH} />
          No phone listed
        </span>
      )}
        <a
          href={directionsUrl(facility.lat, facility.lon)}
          target="_blank"
          rel="noopener noreferrer"
          onClick={stop}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-300 hover:text-brand-200 hover:underline"
        >
          <Icon
            path={
              <>
                <path d="M12 21s-7-5.6-7-11a7 7 0 1 1 14 0c0 5.4-7 11-7 11Z" />
                <circle cx="12" cy="10" r="2.5" />
              </>
            }
          />
          Directions
        </a>

        {site && (
          <a
            href={site}
            target="_blank"
            rel="noopener noreferrer"
            onClick={stop}
            className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-300 hover:text-brand-200 hover:underline"
          >
            <Icon
              path={
                <>
                  <circle cx="12" cy="12" r="9" />
                  <path d="M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18Z" />
                </>
              }
            />
            Website
          </a>
        )}

        {facility.email && (
          <a
            href={`mailto:${facility.email}`}
            onClick={stop}
            className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-300 hover:text-brand-200 hover:underline"
          >
            <Icon
              path={
                <>
                  <rect x="3" y="5" width="18" height="14" rx="2" />
                  <path d="m3 7 9 6 9-6" />
                </>
              }
            />
            Email
          </a>
        )}
    </div>
  );
}

function EmptyState({ icon, title, hint, tone = "slate" }) {
  const tones = {
    slate: "border-slate-800 bg-slate-950/40 text-slate-400",
    danger: "border-red-500/40 bg-red-950/30 text-red-200",
  };
  return (
    <div
      className={`flex flex-1 flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-6 text-center ${tones[tone]}`}
    >
      <div className="text-2xl opacity-80">{icon}</div>
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="max-w-xs text-xs opacity-75">{hint}</p>}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="animate-pulse rounded-lg border border-slate-800 bg-slate-900/60 p-3"
        >
          <div className="mb-2 h-3.5 w-2/3 rounded bg-slate-700/60" />
          <div className="h-2.5 w-1/3 rounded bg-slate-800" />
        </div>
      ))}
    </div>
  );
}

export function FacilityList({
  facilities,
  loading,
  error,
  selectedCity,
  selectedId,
  onSelect,
  columns = 1,
}) {
  if (!selectedCity) {
    return (
      <EmptyState
        icon="🗺️"
        title="Pick a city to begin"
        hint="Choose a KPK city to discover hospitals, clinics, BHUs and RHCs nearby."
      />
    );
  }

  if (loading) return <Skeleton />;

  if (error) {
    return (
      <EmptyState icon="⚠️" tone="danger" title="Couldn't load facilities" hint={error} />
    );
  }

  if (!facilities.length) {
    return (
      <EmptyState
        icon="🔍"
        title={`No matches in ${selectedCity}`}
        hint="Try clearing the filters — OpenStreetMap coverage here may be incomplete."
      />
    );
  }

  return (
    <ul
      className={
        columns > 1
          ? "grid gap-2 sm:grid-cols-2 xl:grid-cols-3"
          : "space-y-2"
      }
    >
      {facilities.map((f) => {
        const style = styleForType(f.facility_type);
        const isSelected = selectedId === f.osm_id;
        return (
          <li key={f.osm_id}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => onSelect(isSelected ? null : f.osm_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(isSelected ? null : f.osm_id);
                }
              }}
              className={`h-full cursor-pointer rounded-lg border px-3 py-2.5 text-left transition ${
                isSelected
                  ? "border-brand-500/70 bg-brand-500/10 shadow-sm shadow-brand-500/20"
                  : "border-slate-800 bg-slate-900/70 hover:border-slate-700 hover:bg-slate-900"
              }`}
            >
              <div className="flex items-start gap-2.5">
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${style.dot}`}
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold leading-snug text-slate-100">
                    {f.name || "Unnamed facility"}
                  </h3>
                  {f.address && (
                    <p className="mt-0.5 text-[11px] text-slate-400">{f.address}</p>
                  )}

                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    {f.facility_type && (
                      <Badge className={style.badge}>{f.facility_type}</Badge>
                    )}
                    {f.ownership && (
                      <Badge
                        className={
                          f.ownership === "government"
                            ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                            : "border-indigo-500/40 bg-indigo-500/10 text-indigo-200"
                        }
                      >
                        {f.ownership === "government" ? "Govt" : "Private"}
                      </Badge>
                    )}
                    {f.is_emergency && (
                      <Badge className="border-red-500/40 bg-red-500/10 text-red-200">
                        Emergency
                      </Badge>
                    )}
                    {f.is_24_7 && (
                      <Badge className="border-teal-500/40 bg-teal-500/10 text-teal-200">
                        24/7
                      </Badge>
                    )}
                  </div>

                  <ContactRow facility={f} />
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
