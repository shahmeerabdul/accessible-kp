from __future__ import annotations

import logging
import math
import os
import re
from typing import Any, Dict, List

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Which upstream to pull facility data from: "healthsites" or "overpass".
FACILITIES_PROVIDER = os.environ.get("FACILITIES_PROVIDER", "healthsites").strip().lower()

# healthsites.io -- a purpose-built health facility API (OSM data, curated by
# HOT). Needs a free API key: sign in at https://healthsites.io/ with an
# OpenStreetMap account and generate one from your profile page.
HEALTHSITES_API_URL = os.environ.get("HEALTHSITES_API_URL", "https://healthsites.io/api/v3/facilities/")
HEALTHSITES_API_KEY = os.environ.get("HEALTHSITES_API_KEY", "")

OVERPASS_API_URL = os.environ.get("OVERPASS_API_URL", "https://overpass.openstreetmap.fr/api/interpreter")

# Cache timeout in seconds (e.g. 10 minutes)
CACHE_TTL = int(os.environ.get("FACILITIES_CACHE_TTL", "600"))

# Radius (meters) searched around each city's center point.
CITY_SEARCH_RADIUS_METERS = int(os.environ.get("CITY_SEARCH_RADIUS_METERS", "12000"))

# Most facilities fetched from a provider for one city. A city is fetched (and
# cached) once at this size; the API filters and applies the caller's limit on
# top, so filters see every fetched facility, not just the first page of them.
FETCH_CAP = 500

# Overpass requires a descriptive User-Agent; public instances 406-reject
# requests carrying a generic client User-Agent (e.g. python-requests/...).
OVERPASS_USER_AGENT = os.environ.get(
    "OVERPASS_USER_AGENT", "AccessibleKPK/1.0 (+https://github.com/shahmeerabdul/accessible-kp)"
)

# City center coordinates (lat, lon). OSM's administrative boundaries for
# these cities are tagged with local-script names (Urdu/Pashto) under `name`,
# with the English name -- when present -- often under `name:en` and not an
# exact match (e.g. "Peshawar City Tehsil"). Matching on `area["name"=city]`
# therefore never resolves and silently returns zero results. Searching by
# radius around a known point sidesteps that tagging inconsistency entirely.
#
# The main town of each KPK district. Coordinates for the newer entries were
# looked up in OpenStreetMap (Nominatim) and checked against the district named
# in the result. Keep this in sync with frontend/src/constants/cities.js (a test
# enforces it) and keep entries more than a few km apart, or two options would
# return almost the same facilities.
CITY_CENTERS: Dict[str, tuple[float, float]] = {
    "Abbottabad": (34.1463, 73.2117),
    "Alpuri": (34.9204, 72.6326),  # Shangla
    "Bannu": (32.9853, 70.6027),
    "Batkhela": (34.6134, 71.9677),  # Malakand
    "Battagram": (34.6786, 73.0281),
    "Charsadda": (34.1520, 71.7380),
    "Chitral": (35.8509, 71.7902),
    "Daggar": (34.5106, 72.4849),  # Buner
    "Dassu": (35.2686, 73.2240),  # Upper Kohistan
    "Dera Ismail Khan": (31.8313, 70.9022),
    "Dir": (35.2080, 71.8780),  # Upper Dir
    "Ghalanai": (34.3230, 71.3996),  # Mohmand
    "Hangu": (33.5280, 71.0575),
    "Haripur": (33.9964, 72.9337),
    "Judba": (34.6124, 72.7890),  # Torghar
    "Kalaya": (33.7475, 70.9621),  # Orakzai
    "Karak": (33.1160, 71.0951),
    "Khar": (34.7350, 71.5251),  # Bajaur
    "Kohat": (33.5900, 71.4400),
    "Lakki Marwat": (32.6057, 70.9114),
    "Landi Kotal": (34.0937, 71.1466),  # Khyber
    "Mansehra": (34.3329, 73.1997),
    "Mardan": (34.1986, 72.0404),
    "Mingora": (34.7717, 72.3604),  # Swat
    "Miranshah": (33.0018, 70.0671),  # North Waziristan
    "Nowshera": (34.0158, 71.9761),
    "Parachinar": (33.8968, 70.1001),  # Kurram
    "Pattan": (35.1102, 73.0052),  # Lower Kohistan (also covers Kolai-Palas)
    "Peshawar": (34.0151, 71.5249),
    "Sararogha": (32.5131, 70.0263),  # South Waziristan
    "Swabi": (34.1262, 72.4743),
    "Tank": (32.2097, 70.3881),
    "Timergara": (34.8291, 71.8427),  # Lower Dir
    "Wana": (32.3074, 69.5907),  # South Waziristan
}

SUPPORTED_CITIES = sorted(CITY_CENTERS)

CITY_COORDINATES: Dict[str, tuple[float, float]] = {
    name.lower(): center for name, center in CITY_CENTERS.items()
}

SUPPORTED_CITIES_LOWER = set(CITY_COORDINATES)


def is_supported_city(city: str) -> bool:
    return city.strip().lower() in SUPPORTED_CITIES_LOWER


def get_city_center(city: str) -> tuple[float, float] | None:
    return CITY_COORDINATES.get(city.strip().lower())


class FacilityProviderError(Exception):
    """
    Raised when an upstream facility data provider fails.

    The message is returned to API clients, so it must stay generic: never put
    request URLs or raw exception text in it (healthsites calls carry the API
    key in the query string, and `requests` exceptions include the full URL).
    Log the details server-side instead.
    """


def build_overpass_query(center: tuple[float, float], limit: int | None = FETCH_CAP) -> str:
    """
    Build an Overpass QL query to fetch healthcare facilities within
    CITY_SEARCH_RADIUS_METERS of a (lat, lon) point.
    """
    lat, lon = center
    radius = CITY_SEARCH_RADIUS_METERS

    core = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});
      way["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});
      relation["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});

      node["healthcare"~"hospital|clinic|centre|doctor"](around:{radius},{lat},{lon});
      way["healthcare"~"hospital|clinic|centre|doctor"](around:{radius},{lat},{lon});
      relation["healthcare"~"hospital|clinic|centre|doctor"](around:{radius},{lat},{lon});
    );
    """

    if limit and limit > 0:
        return core + f"out center {limit};"
    return core + "out center;"


def infer_facility_type(tags: Dict[str, Any]) -> str:
    healthcare = tags.get("healthcare", "").lower()
    amenity = tags.get("amenity", "").lower()
    name = tags.get("name", "").lower()

    # Whole-word matches only, so e.g. "Abhuman Clinic" is not a BHU.
    if re.search(r"\bbhus?\b", name) or "basic health unit" in name:
        return "BHU"
    if re.search(r"\brhcs?\b", name) or re.search(r"rural health cent(re|er)", name):
        return "RHC"

    if healthcare == "hospital" or amenity == "hospital":
        return "Hospital"
    if healthcare in {"clinic", "centre", "doctor"} or amenity in {"clinic", "doctors"}:
        return "Clinic"

    if healthcare:
        return healthcare.title()
    if amenity:
        return amenity.title()
    return ""


GOV_TAG_PATTERN = re.compile(r"\b(government|govt|public|ministry of health|health department)\b")
PRIVATE_TAG_PATTERN = re.compile(r"\b(private|pvt)\b")

# Name markers that identify public-sector facilities in Pakistan.
GOV_NAME_PATTERN = re.compile(
    r"\b(dhq|thq|bhus?|rhcs?|govt|government)\b"
    r"|district headquarters?|tehsil headquarters?|basic health unit"
    r"|rural health cent(re|er)|civil (hospital|dispensary)"
)


def infer_ownership(tags: Dict[str, Any]) -> str:
    """
    Decide if a facility is government or private.

    Explicit operator/ownership tags win. Otherwise fall back to unmistakable
    government markers in the name. Anything else is unknown ("") rather than a
    guess -- e.g. the word "clinic" says nothing about who owns it.
    """
    operator_type = tags.get("operator:type", "").lower()
    ownership = tags.get("ownership", "").lower()
    operator = tags.get("operator", "").lower()
    name = tags.get("name", "").lower()

    text = " ".join([operator_type, ownership, operator])

    if GOV_TAG_PATTERN.search(text):
        return "government"
    if PRIVATE_TAG_PATTERN.search(text):
        return "private"
    if GOV_NAME_PATTERN.search(name):
        return "government"

    return ""


def infer_is_24_7(tags: Dict[str, Any]) -> bool | None:
    h = tags.get("opening_hours")
    if not h:
        return None
    h = h.lower()
    if "24/7" in h or "24-7" in h or "24 hours" in h:
        return True
    return None


def infer_is_emergency(tags: Dict[str, Any]) -> bool | None:
    emergency = tags.get("emergency")
    if not emergency:
        return None
    emergency = emergency.lower()
    if emergency in {"yes", "designated"}:
        return True
    if emergency in {"no"}:
        return False
    return None


def infer_wheelchair(tags: Dict[str, Any]) -> str:
    """
    Wheelchair accessibility from the OSM `wheelchair` tag: "yes", "limited",
    "no", or "" when unknown. (`designated` means built specifically for
    wheelchair users, so it counts as "yes".)
    """
    value = str(tags.get("wheelchair", "")).strip().lower()
    if value in {"yes", "designated"}:
        return "yes"
    if value in {"limited", "no"}:
        return value
    return ""


def build_phone(tags: Dict[str, Any]) -> str:
    for key in ("phone", "contact:phone", "contact:mobile", "phone:mobile", "mobile"):
        value = tags.get(key)
        if value:
            return str(value)
    return ""


def build_address(tags: Dict[str, Any]) -> str:
    parts = [
        tags.get("addr:housename"),
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city") or tags.get("addr:town"),
    ]
    return ", ".join(p for p in parts if p)


def make_osm_id(osm_type: Any, osm_id: Any) -> str:
    """
    Unique id for a facility, e.g. "way/123". OSM numbers nodes, ways and
    relations separately, so the bare numeric id can collide across types.
    """
    if osm_type:
        return f"{osm_type}/{osm_id}"
    return str(osm_id)


def dedupe_facilities(facilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop repeated facilities (same osm_id), keeping the first occurrence."""
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for facility in facilities:
        if facility["osm_id"] in seen:
            continue
        seen.add(facility["osm_id"])
        unique.append(facility)
    return unique


def normalize_element(element: Dict[str, Any]) -> Dict[str, Any]:
    tags = element.get("tags", {}) or {}
    lat = element.get("lat")
    lon = element.get("lon")

    # For ways/relations Overpass returns a `center` object
    if (lat is None or lon is None) and "center" in element:
        lat = element["center"].get("lat")
        lon = element["center"].get("lon")

    if lat is None or lon is None:
        raise FacilityProviderError("Missing coordinates for element")

    facility = {
        "osm_id": make_osm_id(element.get("type"), element.get("id")),
        "name": tags.get("name", ""),
        "facility_type": infer_facility_type(tags),
        "address": build_address(tags),
        "phone": build_phone(tags),
        "website": tags.get("website") or tags.get("contact:website") or "",
        "email": tags.get("email") or tags.get("contact:email") or "",
        "is_24_7": infer_is_24_7(tags),
        "is_emergency": infer_is_emergency(tags),
        "wheelchair": infer_wheelchair(tags),
        "ownership": infer_ownership(tags),
        "lat": lat,
        "lon": lon,
    }
    return facility


def fetch_facilities_from_overpass(center: tuple[float, float]) -> List[Dict[str, Any]]:
    query = build_overpass_query(center, FETCH_CAP)

    try:
        response = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            headers={"User-Agent": OVERPASS_USER_AGENT},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("Overpass request failed: %s", type(exc).__name__)
        raise FacilityProviderError("Failed to connect to the Overpass API") from None

    if response.status_code != 200:
        raise FacilityProviderError(f"Overpass API returned status {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise FacilityProviderError("Overpass API returned an invalid response") from exc

    elements = data.get("elements", [])

    facilities: List[Dict[str, Any]] = []
    for el in elements:
        try:
            facilities.append(normalize_element(el))
        except FacilityProviderError:
            # Skip malformed elements
            continue

    return dedupe_facilities(facilities)


def build_bbox(lat: float, lon: float, radius_m: int) -> tuple[float, float, float, float]:
    """(minLng, minLat, maxLng, maxLat) box approximating a radius around a point."""
    lat_delta = radius_m / 111_320.0
    lon_delta = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))
    return (lon - lon_delta, lat - lat_delta, lon + lon_delta, lat + lat_delta)


def healthsites_attrs_to_tags(attrs: Dict[str, Any]) -> Dict[str, str]:
    """
    Map healthsites' flat model-field names onto the OSM tag keys the
    infer_* helpers already understand, so both providers share one
    normalization path.
    """
    mapping = {
        "name": "name",
        "amenity": "amenity",
        "healthcare": "healthcare",
        "operator": "operator",
        "operator_type": "operator:type",
        "contact_number": "phone",
        "url": "website",
        # Not seen in healthsites responses so far; mapped defensively so an
        # email is shown if the API ever returns one under either name.
        "email": "email",
        "contact_email": "email",
        "opening_hours": "opening_hours",
        "emergency": "emergency",
        # Not present in the healthsites responses checked so far (so accessibility
        # data mostly comes from the Overpass provider); mapped in case it appears.
        "wheelchair": "wheelchair",
        "addr_housenumber": "addr:housenumber",
        "addr_street": "addr:street",
        "addr_city": "addr:city",
    }
    tags: Dict[str, str] = {}
    for source_key, tag_key in mapping.items():
        if tag_key in tags:
            continue  # first matching source wins
        value = attrs.get(source_key)
        if value is not None and str(value).strip():
            tags[tag_key] = str(value)
    return tags


def normalize_healthsites_record(record: Dict[str, Any]) -> Dict[str, Any]:
    attrs = record.get("attributes") or {}
    coords = (record.get("centroid") or {}).get("coordinates") or []
    if len(coords) < 2:
        raise FacilityProviderError("Missing coordinates for facility")

    # GeoJSON order is [lon, lat]
    lon, lat = coords[0], coords[1]
    tags = healthsites_attrs_to_tags(attrs)

    return {
        "osm_id": make_osm_id(record.get("osm_type"), record.get("osm_id")),
        "name": tags.get("name", ""),
        "facility_type": infer_facility_type(tags),
        "address": build_address(tags),
        "phone": tags.get("phone", ""),
        "website": tags.get("website", ""),
        "email": tags.get("email", ""),
        "is_24_7": infer_is_24_7(tags),
        "is_emergency": infer_is_emergency(tags),
        "wheelchair": infer_wheelchair(tags),
        "ownership": infer_ownership(tags),
        "lat": lat,
        "lon": lon,
    }


def fetch_facilities_from_healthsites(center: tuple[float, float]) -> List[Dict[str, Any]]:
    if not HEALTHSITES_API_KEY:
        raise FacilityProviderError(
            "HEALTHSITES_API_KEY is not set. Sign in at https://healthsites.io/ with an "
            "OpenStreetMap account, generate an API key on your profile page, and add it "
            "to backend/.env as HEALTHSITES_API_KEY."
        )

    lat, lon = center
    min_lng, min_lat, max_lng, max_lat = build_bbox(lat, lon, CITY_SEARCH_RADIUS_METERS)
    extent = f"{min_lng},{min_lat},{max_lng},{max_lat}"

    target = FETCH_CAP
    per_page = min(target, 100)
    facilities: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    page = 1

    while len(facilities) < target and page <= 10:
        try:
            response = requests.get(
                HEALTHSITES_API_URL,
                params={
                    "api-key": HEALTHSITES_API_KEY,
                    "page": page,
                    "limit": per_page,
                    "extent": extent,
                    "output": "json",
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            # Don't log or return str(exc): it contains the request URL, which
            # includes the api-key query parameter.
            logger.error("healthsites.io request failed: %s", type(exc).__name__)
            raise FacilityProviderError("Failed to connect to healthsites.io") from None

        if response.status_code == 403:
            # Surface healthsites' own message -- it distinguishes a bad key from
            # one that is simply still awaiting admin approval.
            detail = ""
            try:
                detail = (response.json() or {}).get("detail", "")
            except ValueError:
                pass
            raise FacilityProviderError(
                f"healthsites.io rejected the request: {detail}"
                if detail
                else "healthsites.io rejected the API key (403)."
            )
        if response.status_code != 200:
            raise FacilityProviderError(
                f"healthsites.io returned status {response.status_code}"
            )

        try:
            records = response.json()
        except ValueError as exc:
            raise FacilityProviderError("healthsites.io returned an invalid response") from exc

        if not records:
            break

        for record in records:
            try:
                facility = normalize_healthsites_record(record)
            except FacilityProviderError:
                continue
            if facility["osm_id"] in seen_ids:
                continue
            seen_ids.add(facility["osm_id"])
            facilities.append(facility)

        if len(records) < per_page:
            break
        page += 1

    return facilities[:target]


def _matches_query(facility: Dict[str, Any], words: List[str]) -> bool:
    """True if every search word appears in the facility's name or address."""
    haystack = f"{facility.get('name', '')} {facility.get('address', '')}".casefold()
    return all(word in haystack for word in words)


def filter_facilities(
    facilities: List[Dict[str, Any]],
    ownership: str = "",
    emergency_only: bool = False,
    open_24_7_only: bool = False,
    wheelchair_only: bool = False,
    query: str = "",
) -> List[Dict[str, Any]]:
    """
    Keep only facilities matching every given filter (empty/False = no filter).

    `query` is a free-text search: every word must appear (case-insensitively)
    in the facility's name or address.
    """
    words = query.casefold().split()
    return [
        f
        for f in facilities
        if (not ownership or f.get("ownership") == ownership)
        and (not emergency_only or f.get("is_emergency"))
        and (not open_24_7_only or f.get("is_24_7"))
        and (not wheelchair_only or f.get("wheelchair") == "yes")
        and (not words or _matches_query(f, words))
    ]


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres (haversine)."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def with_distance(facilities: List[Dict[str, Any]], lat: float, lon: float) -> List[Dict[str, Any]]:
    """Copies of the facilities with `distance_km` (from lat/lon) added. Never mutates the cached list."""
    return [{**f, "distance_km": round(distance_km(lat, lon, f["lat"], f["lon"]), 1)} for f in facilities]


def sort_facilities(facilities: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    """
    Order facilities by "name" (A-Z, unnamed last) or "distance" (nearest first;
    needs `distance_km`, see with_distance). Any other value keeps provider order.
    """
    if sort == "name":
        return sorted(facilities, key=lambda f: (not f.get("name"), (f.get("name") or "").casefold()))
    if sort == "distance":
        return sorted(facilities, key=lambda f: f["distance_km"])
    return list(facilities)


# Rough bounding box of Khyber Pakhtunkhwa (lat_min, lat_max, lon_min, lon_max).
KPK_BOUNDS = (31.0, 36.9, 69.0, 74.2)

# "Near me" coordinates are snapped to this grid (degrees, ~5.5 km) before
# fetching. Without it every distinct GPS reading would be a separate upstream
# call and cache entry; with it the number of cache keys is bounded.
NEAR_ME_GRID_DEGREES = 0.05


def is_in_kpk_area(lat: float, lon: float) -> bool:
    lat_min, lat_max, lon_min, lon_max = KPK_BOUNDS
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def snap_to_grid(lat: float, lon: float) -> tuple[float, float]:
    def snap(value: float) -> float:
        return round(round(value / NEAR_ME_GRID_DEGREES) * NEAR_ME_GRID_DEGREES, 3)

    return snap(lat), snap(lon)


def _load_facilities(cache_key: str, center: tuple[float, float]) -> List[Dict[str, Any]]:
    """Return the cached facilities for `cache_key`, fetching them around `center` on a miss."""
    # A shared cache (Redis) can be unreachable. That must slow the API down
    # (every request goes upstream), not take it down.
    try:
        cached = cache.get(cache_key)
    except Exception as exc:
        logger.warning("Cache read failed, fetching live: %s", type(exc).__name__)
        cached = None
    if cached is not None:
        return cached

    if FACILITIES_PROVIDER == "healthsites":
        facilities = fetch_facilities_from_healthsites(center)
    elif FACILITIES_PROVIDER == "overpass":
        facilities = fetch_facilities_from_overpass(center)
    else:
        raise FacilityProviderError(
            f"Unknown FACILITIES_PROVIDER '{FACILITIES_PROVIDER}' (expected 'healthsites' or 'overpass')"
        )

    try:
        cache.set(cache_key, facilities, CACHE_TTL)
    except Exception as exc:
        logger.warning("Cache write failed: %s", type(exc).__name__)
    return facilities


def get_facilities_by_city(city: str) -> List[Dict[str, Any]]:
    """
    High-level function used by the view.

    Applies basic validation and caching, then calls the configured provider.
    A city is fetched and cached once (up to FETCH_CAP facilities) regardless
    of filters or the caller's limit; the view filters and slices the result.
    """
    city_clean = city.strip()
    if not city_clean:
        raise FacilityProviderError("City name is required")

    center = get_city_center(city_clean)
    if center is None:
        raise FacilityProviderError(f"No known coordinates for city '{city_clean}'")

    return _load_facilities(f"facilities:{FACILITIES_PROVIDER}:{city_clean.lower()}", center)


def get_facilities_near(lat: float, lon: float) -> List[Dict[str, Any]]:
    """
    Facilities around an arbitrary point (a visitor's location), within
    CITY_SEARCH_RADIUS_METERS of the grid cell the point falls in. Cached per cell.
    """
    center = snap_to_grid(lat, lon)
    return _load_facilities(f"facilities:{FACILITIES_PROVIDER}:near:{center[0]}:{center[1]}", center)

