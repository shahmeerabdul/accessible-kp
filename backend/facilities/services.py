from __future__ import annotations

import math
import os
from typing import Any, Dict, List

import requests
from django.core.cache import cache

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
CITY_COORDINATES: Dict[str, tuple[float, float]] = {
    "peshawar": (34.0151, 71.5249),
    "mardan": (34.1986, 72.0404),
    "abbottabad": (34.1463, 73.2117),
    "mingora": (34.7717, 72.3604),
    "swat": (34.7717, 72.3604),
    "kohat": (33.5900, 71.4400),
    "bannu": (32.9853, 70.6027),
    "dera ismail khan": (31.8313, 70.9022),
    "charsadda": (34.1520, 71.7380),
    "nowshera": (34.0158, 71.9761),
    "haripur": (33.9964, 72.9337),
    "mansehra": (34.3329, 73.1997),
}

SUPPORTED_CITIES = [
    "Peshawar",
    "Mardan",
    "Abbottabad",
    "Mingora",
    "Swat",
    "Kohat",
    "Bannu",
    "Dera Ismail Khan",
    "Charsadda",
    "Nowshera",
    "Haripur",
    "Mansehra",
]

SUPPORTED_CITIES_LOWER = {c.lower() for c in SUPPORTED_CITIES}


def is_supported_city(city: str) -> bool:
    return city.strip().lower() in SUPPORTED_CITIES_LOWER


def get_city_center(city: str) -> tuple[float, float] | None:
    return CITY_COORDINATES.get(city.strip().lower())


class FacilityProviderError(Exception):
    """Raised when an upstream facility data provider fails."""


def build_overpass_query(city: str, limit: int | None = None) -> str:
    """
    Build an Overpass QL query to fetch healthcare facilities near the given
    city's center point.
    """
    center = get_city_center(city)
    if center is None:
        raise FacilityProviderError(f"No known coordinates for city '{city}'")
    lat, lon = center
    radius = CITY_SEARCH_RADIUS_METERS

    core = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});
      way["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});
      relation["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});

      node["healthcare"~"hospital|clinic|centre"](around:{radius},{lat},{lon});
      way["healthcare"~"hospital|clinic|centre"](around:{radius},{lat},{lon});
      relation["healthcare"~"hospital|clinic|centre"](around:{radius},{lat},{lon});
    );
    """

    if limit and limit > 0:
        return core + f"out center {limit};"
    return core + "out center;"


def infer_facility_type(tags: Dict[str, Any]) -> str:
    healthcare = tags.get("healthcare", "").lower()
    amenity = tags.get("amenity", "").lower()
    name = tags.get("name", "").lower()

    if "bhu" in name or "basic health unit" in name:
        return "BHU"
    if "rhc" in name or "rural health centre" in name or "rural health center" in name:
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


def infer_ownership(tags: Dict[str, Any]) -> str:
    """
    Try to decide if a facility is government or private based on common OSM tags.
    """
    operator_type = tags.get("operator:type", "").lower()
    ownership = tags.get("ownership", "").lower()
    operator = tags.get("operator", "").lower()

    gov_keywords = ["government", "public", "ministry of health", "health department"]
    private_keywords = ["private", "pvt", "pvt.", "clinic", "trust"]

    text = " ".join([operator_type, ownership, operator])

    if any(k in text for k in gov_keywords):
        return "government"
    if any(k in text for k in private_keywords):
        return "private"

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


def build_address(tags: Dict[str, Any]) -> str:
    parts = [
        tags.get("addr:housename"),
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city") or tags.get("addr:town"),
    ]
    return ", ".join(p for p in parts if p)


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
        "osm_id": str(element.get("id")),
        "name": tags.get("name", ""),
        "facility_type": infer_facility_type(tags),
        "address": build_address(tags),
        "phone": tags.get("phone") or tags.get("contact:phone") or "",
        "is_24_7": infer_is_24_7(tags),
        "is_emergency": infer_is_emergency(tags),
        "ownership": infer_ownership(tags),
        "lat": lat,
        "lon": lon,
    }
    return facility


def fetch_facilities_from_overpass(city: str, limit: int | None = None) -> List[Dict[str, Any]]:
    query = build_overpass_query(city, limit)

    try:
        response = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            headers={"User-Agent": OVERPASS_USER_AGENT},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise FacilityProviderError(f"Failed to connect to Overpass API: {exc}") from exc

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

    return facilities


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
        "opening_hours": "opening_hours",
        "emergency": "emergency",
        "addr_housenumber": "addr:housenumber",
        "addr_street": "addr:street",
        "addr_city": "addr:city",
    }
    tags: Dict[str, str] = {}
    for source_key, tag_key in mapping.items():
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
        "osm_id": str(record.get("osm_id")),
        "name": tags.get("name", ""),
        "facility_type": infer_facility_type(tags),
        "address": build_address(tags),
        "phone": tags.get("phone", ""),
        "is_24_7": infer_is_24_7(tags),
        "is_emergency": infer_is_emergency(tags),
        "ownership": infer_ownership(tags),
        "lat": lat,
        "lon": lon,
    }


def fetch_facilities_from_healthsites(city: str, limit: int | None = None) -> List[Dict[str, Any]]:
    if not HEALTHSITES_API_KEY:
        raise FacilityProviderError(
            "HEALTHSITES_API_KEY is not set. Sign in at https://healthsites.io/ with an "
            "OpenStreetMap account, generate an API key on your profile page, and add it "
            "to backend/.env as HEALTHSITES_API_KEY."
        )

    center = get_city_center(city)
    if center is None:
        raise FacilityProviderError(f"No known coordinates for city '{city}'")

    lat, lon = center
    min_lng, min_lat, max_lng, max_lat = build_bbox(lat, lon, CITY_SEARCH_RADIUS_METERS)
    extent = f"{min_lng},{min_lat},{max_lng},{max_lat}"

    target = limit or 500
    per_page = min(target, 100)
    facilities: List[Dict[str, Any]] = []
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
            raise FacilityProviderError(f"Failed to connect to healthsites.io: {exc}") from exc

        if response.status_code == 403:
            raise FacilityProviderError(
                "healthsites.io rejected the API key. Regenerate it from your profile page."
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
                facilities.append(normalize_healthsites_record(record))
            except FacilityProviderError:
                continue

        if len(records) < per_page:
            break
        page += 1

    return facilities[:target]


def get_facilities_by_city(city: str, limit: int | None = None) -> List[Dict[str, Any]]:
    """
    High-level function used by the view.
    Applies basic validation and caching, then calls the configured provider.
    """
    city_clean = city.strip()
    if not city_clean:
        raise FacilityProviderError("City name is required")

    cache_key = f"facilities:{FACILITIES_PROVIDER}:{city_clean.lower()}:{limit or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if FACILITIES_PROVIDER == "healthsites":
        facilities = fetch_facilities_from_healthsites(city_clean, limit)
    elif FACILITIES_PROVIDER == "overpass":
        facilities = fetch_facilities_from_overpass(city_clean, limit)
    else:
        raise FacilityProviderError(
            f"Unknown FACILITIES_PROVIDER '{FACILITIES_PROVIDER}' (expected 'healthsites' or 'overpass')"
        )

    cache.set(cache_key, facilities, CACHE_TTL)
    return facilities

