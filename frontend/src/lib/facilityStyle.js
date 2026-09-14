// Shared facility-type styling so the list and the map stay visually in sync.
export const TYPE_STYLES = {
  Hospital: {
    hex: "#fb7185",
    badge: "border-rose-500/40 bg-rose-500/10 text-rose-200",
    dot: "bg-rose-400",
  },
  Clinic: {
    hex: "#38bdf8",
    badge: "border-sky-500/40 bg-sky-500/10 text-sky-200",
    dot: "bg-sky-400",
  },
  BHU: {
    hex: "#fbbf24",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-200",
    dot: "bg-amber-400",
  },
  RHC: {
    hex: "#c084fc",
    badge: "border-purple-500/40 bg-purple-500/10 text-purple-200",
    dot: "bg-purple-400",
  },
};

export const FALLBACK_STYLE = {
  hex: "#94a3b8",
  badge: "border-slate-600/50 bg-slate-700/30 text-slate-300",
  dot: "bg-slate-400",
};

export function styleForType(type) {
  return TYPE_STYLES[type] || FALLBACK_STYLE;
}
