import { styleForType } from "../lib/facilityStyle.js";

/** Square letter marker for a facility type (decorative; the type is also written out). */
export function TypeMark({ type }) {
  const { hex, letter } = styleForType(type);
  return (
    <span
      aria-hidden="true"
      style={{ background: hex }}
      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-base font-bold text-white"
    >
      {letter}
    </span>
  );
}
