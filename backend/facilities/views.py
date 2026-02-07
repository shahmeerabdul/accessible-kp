from __future__ import annotations

from typing import Any, List

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import FacilitySerializer
from .services import OverpassError, get_facilities_by_city


class FacilityListView(APIView):
    """
    GET /api/facilities?city=<city_name>&limit=<int>

    Acts as a proxy to the Overpass API, returning normalized healthcare
    facilities for cities in Khyber Pakhtunkhwa.
    """

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        city = request.query_params.get("city")
        if not city:
            return Response(
                {"detail": "Query parameter 'city' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit_param = request.query_params.get("limit")
        limit: int | None = None
        if limit_param:
            try:
                limit = max(1, int(limit_param))
            except ValueError:
                return Response(
                    {"detail": "Query parameter 'limit' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            facilities_data: List[dict] = get_facilities_by_city(city, limit)
        except OverpassError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        serializer = FacilitySerializer(facilities_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

