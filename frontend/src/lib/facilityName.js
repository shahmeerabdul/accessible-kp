/** Display title for a facility; many OSM records have no name. */
export function facilityTitle(facility) {
  if (facility.name) return facility.name;
  return `Unnamed ${facility.facility_type || "facility"}`;
}
