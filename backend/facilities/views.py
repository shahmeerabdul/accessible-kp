from __future__ import annotations

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
    get_facilities_by_city,
    is_supported_city,
)

MAX_LIMIT = FETCH_CAP
OWNERSHIP_VALUES = {"government", "private"}
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


class FacilityListView(APIView):
    """
    GET /api/facilities?city=<city_name>&limit=<int>
        [&ownership=government|private][&emergency=true][&open_24_7=true]

    Returns normalized healthcare facilities for cities in Khyber Pakhtunkhwa,
    fetched from the configured provider (healthsites.io or Overpass).

    Filters are applied to every facility fetched for the city *before* the
    limit, so a filter never misses matches that sit beyond the first `limit`.

    Response headers (exposed to browsers via CORS):
      X-Total-Count      number of facilities matching the filters
      X-Upstream-Capped  "true" if the city hit the fetch cap, i.e. more
                         facilities may exist than were fetched
    """

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        params = request.query_params

        city = params.get("city")
        if not city:
            return Response(
                {"detail": "Query parameter 'city' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not is_supported_city(city):
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
        if emergency_only is None or open_24_7_only is None:
            return Response(
                {"detail": "Query parameters 'emergency' and 'open_24_7' must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            all_facilities: List[dict] = get_facilities_by_city(city)
        except FacilityProviderError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        matching = filter_facilities(all_facilities, ownership, emergency_only, open_24_7_only)

        serializer = FacilitySerializer(matching[:limit], many=True)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response["X-Total-Count"] = str(len(matching))
        response["X-Upstream-Capped"] = "true" if len(all_facilities) >= FETCH_CAP else "false"
        return response
