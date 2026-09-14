from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from django.core.cache import cache

OVERPASS_API_URL = os.environ.get("OVERPASS_API_URL", "https://overpass-api.de/api/interpreter")

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


class OverpassError(Exception):
    """Custom exception for Overpass-related issues."""


def build_overpass_query(city: str, limit: int | None = None) -> str:
    """
    Build an Overpass QL query to fetch healthcare facilities near the given
    city's center point.
    """
    center = get_city_center(city)
    if center is None:
        raise OverpassError(f"No known coordinates for city '{city}'")
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
        raise OverpassError("Missing coordinates for element")

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
        raise OverpassError(f"Failed to connect to Overpass API: {exc}") from exc

    if response.status_code != 200:
        raise OverpassError(f"Overpass API returned status {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise OverpassError("Overpass API returned an invalid response") from exc

    elements = data.get("elements", [])

    facilities: List[Dict[str, Any]] = []
    for el in elements:
        try:
            facilities.append(normalize_element(el))
        except OverpassError:
            # Skip malformed elements
            continue

    return facilities


def get_facilities_by_city(city: str, limit: int | None = None) -> List[Dict[str, Any]]:
    """
    High-level function used by the view.
    Applies basic validation, caching, and calls Overpass.
    """
    city_clean = city.strip()
    if not city_clean:
        raise OverpassError("City name is required")

    cache_key = f"facilities:{city_clean.lower()}:{limit or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    facilities = fetch_facilities_from_overpass(city_clean, limit)
    cache.set(cache_key, facilities, CACHE_TTL)
    return facilities

