// Shared facility-type styling so the list and the map stay in sync.
//
// Colour is never the only signal: every type also has a letter (H, C, B, R)
// that is shown on the list marker and inside the map pin.
export const TYPE_STYLES = {
  Hospital: { hex: "#9B1C1C", letter: "H" },
  Clinic: { hex: "#1D4E89", letter: "C" },
  BHU: { hex: "#8A5A00", letter: "B" },
  RHC: { hex: "#5B3A8C", letter: "R" },
};

const FALLBACK_HEX = "#4B5563";

export function styleForType(type) {
  if (TYPE_STYLES[type]) return TYPE_STYLES[type];
  // `type` can be an arbitrary OSM tag value, so only ever use a plain letter.
  const letter = /^[A-Za-z]/.test(type || "") ? type[0].toUpperCase() : "•";
  return { hex: FALLBACK_HEX, letter };
}
