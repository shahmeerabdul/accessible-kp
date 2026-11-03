from __future__ import annotations

import math
from typing import Any, List

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import FacilitySerializer
from .services import (
    FETCH_CAP,
    FacilityProviderError,
    filter_facilities,
    get_city_center,
    get_facilities_by_city,
    get_facilities_near,
    is_in_kpk_area,
    is_supported_city,
    sort_facilities,
    with_distance,
)

MAX_LIMIT = FETCH_CAP
MAX_QUERY_LENGTH = 100
OWNERSHIP_VALUES = {"government", "private"}
SORT_VALUES = {"", "name", "distance"}
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"", "0", "false", "no", "off"}


class HealthView(APIView):
    """
    GET /api/health -- liveness check for load balancers and uptime monitors.

    Deliberately cheap: it never calls an upstream provider, and it is exempt
    from the API throttle so frequent health checks are not rate-limited.
    """

    throttle_classes: list = []

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response({"status": "ok"})


def parse_bool(value: str | None) -> bool | None:
    """True/False for a recognised flag value, None if it isn't one."""
    if value is None:
        return False
    value = value.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    return None


def parse_coordinates(params) -> tuple[tuple[float, float] | None, str]:
    """
    Parse the optional `lat` / `lon` pair. Returns ((lat, lon) or None, error message).
    Both must be given together, be real numbers in range, and lie in the KPK area.
    """
    lat_raw, lon_raw = params.get("lat"), params.get("lon")
    if not lat_raw and not lon_raw:
        return None, ""
    if not lat_raw or not lon_raw:
        return None, "Query parameters 'lat' and 'lon' must be given together."
    try:
        lat, lon = float(lat_raw), float(lon_raw)
    except ValueError:
        return None, "Query parameters 'lat' and 'lon' must be numbers."
    if not (math.isfinite(lat) and math.isfinite(lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, "Query parameters 'lat' and 'lon' are not valid coordinates."
    if not is_in_kpk_area(lat, lon):
        return None, "That location is outside the supported Khyber Pakhtunkhwa area."
    return (lat, lon), ""


class FacilityListView(APIView):
    """
    GET /api/facilities?city=<city_name>            (or ?lat=<float>&lon=<float> for "near me")
        [&limit=<int>][&ownership=government|private][&emergency=true]
        [&open_24_7=true][&wheelchair=true][&q=<text>][&sort=name|distance]

    Returns normalized healthcare facilities in Khyber Pakhtunkhwa, fetched
    from the configured provider (healthsites.io or Overpass).

    Give a `city`, or the visitor's `lat` and `lon` (or both: the city is
    searched and distances are measured from the visitor).

    Filters and the text search `q` (every word must appear in the name or
    address) are applied to every fetched facility *before* sorting and the
    limit, so they never miss matches beyond the first `limit`.

    `sort=name` is A-Z (unnamed last); `sort=distance` is nearest first. With
    `lat`/`lon` the default order is nearest first. Each facility has
    `distance_km` when a reference point is known (the visitor, or the city
    centre for `sort=distance`), otherwise null.

    Response headers (exposed to browsers via CORS):
      X-Total-Count      number of facilities matching the filters
      X-Upstream-Capped  "true" if the search area hit the fetch cap, i.e.
                         more facilities may exist than were fetched
    """

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        params = request.query_params

        user_point, coordinates_error = parse_coordinates(params)
        if coordinates_error:
            return Response({"detail": coordinates_error}, status=status.HTTP_400_BAD_REQUEST)

        city = params.get("city")
        if not city and not user_point:
            return Response(
                {"detail": "Provide the query parameter 'city', or 'lat' and 'lon'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if city and not is_supported_city(city):
            return Response(
                {"detail": f"'{city}' is not a supported KPK city."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit: int = MAX_LIMIT
        limit_param = params.get("limit")
        if limit_param:
            try:
                limit = min(MAX_LIMIT, max(1, int(limit_param)))
            except ValueError:
                return Response(
                    {"detail": "Query parameter 'limit' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        ownership = (params.get("ownership") or "").strip().lower()
        if ownership and ownership not in OWNERSHIP_VALUES:
            return Response(
                {"detail": "Query parameter 'ownership' must be 'government' or 'private'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emergency_only = parse_bool(params.get("emergency"))
        open_24_7_only = parse_bool(params.get("open_24_7"))
        wheelchair_only = parse_bool(params.get("wheelchair"))
        if emergency_only is None or open_24_7_only is None or wheelchair_only is None:
            return Response(
                {"detail": "Query parameters 'emergency', 'open_24_7' and 'wheelchair' must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sort = (params.get("sort") or "").strip().lower()
        if sort not in SORT_VALUES:
            return Response(
                {"detail": "Query parameter 'sort' must be 'name' or 'distance'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        query = " ".join((params.get("q") or "").split())[:MAX_QUERY_LENGTH]

        try:
            if city:
                all_facilities: List[dict] = get_facilities_by_city(city)
            else:
                all_facilities = get_facilities_near(*user_point)
        except FacilityProviderError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        matching = filter_facilities(
            all_facilities,
            ownership=ownership,
            emergency_only=emergency_only,
            open_24_7_only=open_24_7_only,
            wheelchair_only=wheelchair_only,
            query=query,
        )

        # Distance is measured from the visitor if we know where they are,
        # otherwise (for sort=distance) from the city centre.
        reference = user_point or (get_city_center(city) if sort == "distance" else None)
        if reference:
            matching = with_distance(matching, *reference)
        matching = sort_facilities(matching, sort or ("distance" if user_point else ""))

        serializer = FacilitySerializer(matching[:limit], many=True)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response["X-Total-Count"] = str(len(matching))
        response["X-Upstream-Capped"] = "true" if len(all_facilities) >= FETCH_CAP else "false"
        return response
