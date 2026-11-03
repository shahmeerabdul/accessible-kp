"""Accessibility data, text search, sorting, distance and "near me" (issues #14, #15, #25)."""
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from facilities import services
from facilities.services import (
    distance_km,
    filter_facilities,
    infer_wheelchair,
    is_in_kpk_area,
    normalize_element,
    normalize_healthsites_record,
    snap_to_grid,
    sort_facilities,
    with_distance,
)

PESHAWAR = (34.0151, 71.5249)
MARDAN = (34.1986, 72.0404)


def fac(osm_id, name="", address="", lat=34.0, lon=71.5, wheelchair="", ownership=""):
    return {
        "osm_id": osm_id, "name": name, "facility_type": "Hospital", "address": address, "phone": "",
        "website": "", "email": "", "is_24_7": None, "is_emergency": None, "wheelchair": wheelchair,
        "ownership": ownership, "lat": lat, "lon": lon,
    }


class WheelchairTests(SimpleTestCase):
    """#14"""

    def test_inference(self):
        self.assertEqual(infer_wheelchair({"wheelchair": "yes"}), "yes")
        self.assertEqual(infer_wheelchair({"wheelchair": "designated"}), "yes")
        self.assertEqual(infer_wheelchair({"wheelchair": "Limited"}), "limited")
        self.assertEqual(infer_wheelchair({"wheelchair": "no"}), "no")
        self.assertEqual(infer_wheelchair({"wheelchair": "maybe"}), "")
        self.assertEqual(infer_wheelchair({}), "")

    def test_overpass_elements_carry_the_field(self):
        element = {"type": "node", "id": 1, "lat": 1.0, "lon": 2.0, "tags": {"name": "A", "wheelchair": "yes"}}
        self.assertEqual(normalize_element(element)["wheelchair"], "yes")

    def test_healthsites_records_carry_the_field_when_present(self):
        record = {"osm_id": 1, "osm_type": "node", "centroid": {"coordinates": [71.5, 34.0]},
                  "attributes": {"name": "A", "wheelchair": "limited"}}
        self.assertEqual(normalize_healthsites_record(record)["wheelchair"], "limited")
        del record["attributes"]["wheelchair"]
        self.assertEqual(normalize_healthsites_record(record)["wheelchair"], "")

    def test_wheelchair_filter_keeps_only_confirmed_access(self):
        data = [fac("1", wheelchair="yes"), fac("2", wheelchair="limited"), fac("3", wheelchair="no"), fac("4")]
        ids = [f["osm_id"] for f in filter_facilities(data, wheelchair_only=True)]
        self.assertEqual(ids, ["1"])


class TextSearchTests(SimpleTestCase):
    """#15"""

    DATA = [
        fac("1", name="Saidu Group of Teaching Hospital", address="Saidu Sharif, Swat"),
        fac("2", name="Khyber Medical Complex", address="University Road, Peshawar"),
        fac("3", name="", address="Hayatabad, Peshawar"),
    ]

    def ids(self, query):
        return [f["osm_id"] for f in filter_facilities(self.DATA, query=query)]

    def test_case_insensitive_name_match(self):
        self.assertEqual(self.ids("khyber"), ["2"])
        self.assertEqual(self.ids("KHYBER"), ["2"])

    def test_every_word_must_match_in_any_order(self):
        self.assertEqual(self.ids("hospital saidu"), ["1"])
        self.assertEqual(self.ids("hospital peshawar"), [])

    def test_matches_the_address_too(self):
        self.assertEqual(self.ids("peshawar"), ["2", "3"])

    def test_blank_query_matches_everything(self):
        self.assertEqual(self.ids("   "), ["1", "2", "3"])


class DistanceAndSortTests(SimpleTestCase):
    """#15 and #25"""

    def test_distance_between_known_cities(self):
        self.assertAlmostEqual(distance_km(*PESHAWAR, *MARDAN), 52, delta=2)
        self.assertEqual(distance_km(*PESHAWAR, *PESHAWAR), 0)

    def test_with_distance_does_not_mutate_the_input(self):
        original = [fac("1", lat=34.1, lon=71.5)]
        result = with_distance(original, *PESHAWAR)
        self.assertIn("distance_km", result[0])
        self.assertNotIn("distance_km", original[0])

    def test_sort_by_name_puts_unnamed_last(self):
        data = [fac("1", name="zeta"), fac("2", name=""), fac("3", name="Alpha"), fac("4", name="beta")]
        self.assertEqual([f["osm_id"] for f in sort_facilities(data, "name")], ["3", "4", "1", "2"])

    def test_sort_by_distance_is_nearest_first(self):
        near, far = fac("near", lat=34.02, lon=71.53), fac("far", lat=34.5, lon=72.0)
        ordered = sort_facilities(with_distance([far, near], *PESHAWAR), "distance")
        self.assertEqual([f["osm_id"] for f in ordered], ["near", "far"])

    def test_unknown_sort_keeps_provider_order(self):
        data = [fac("b"), fac("a")]
        self.assertEqual([f["osm_id"] for f in sort_facilities(data, "")], ["b", "a"])


class NearMeServiceTests(SimpleTestCase):
    """#25"""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_area_check(self):
        self.assertTrue(is_in_kpk_area(*PESHAWAR))
        self.assertFalse(is_in_kpk_area(25.0, 67.0))  # Karachi
        self.assertFalse(is_in_kpk_area(51.5, -0.1))  # London

    def test_nearby_points_snap_to_the_same_cell_and_far_ones_do_not(self):
        self.assertEqual(snap_to_grid(34.0151, 71.5249), snap_to_grid(34.0101, 71.5101))
        self.assertNotEqual(snap_to_grid(34.0151, 71.5249), snap_to_grid(34.2, 72.0))

    def test_one_upstream_fetch_per_grid_cell(self):
        with mock.patch.object(services, "FACILITIES_PROVIDER", "healthsites"), \
                mock.patch.object(services, "fetch_facilities_from_healthsites", return_value=[fac("1")]) as fetch:
            services.get_facilities_near(34.0151, 71.5249)
            services.get_facilities_near(34.0101, 71.5101)  # same cell: cached
            services.get_facilities_near(34.5, 72.5)  # another cell: fetched
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(fetch.call_args_list[0].args[0], snap_to_grid(34.0151, 71.5249))


class SearchApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.data = [
            fac("far", name="Far Hospital", lat=34.5, lon=72.0, wheelchair="yes"),
            fac("near", name="Near Clinic", lat=34.02, lon=71.53, wheelchair="no"),
            fac("mid", name="", lat=34.1, lon=71.6),
        ]

    def get(self, patch="facilities.views.get_facilities_by_city", **params):
        with mock.patch(patch, return_value=self.data):
            return self.client.get("/api/facilities", params)

    def test_near_me_orders_nearest_first_and_reports_distance(self):
        response = self.get("facilities.views.get_facilities_near", lat="34.0151", lon="71.5249")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([f["osm_id"] for f in body], ["near", "mid", "far"])
        self.assertEqual(body[0]["distance_km"], round(distance_km(*PESHAWAR, 34.02, 71.53), 1))
        self.assertEqual(response["X-Total-Count"], "3")

    def test_near_me_does_not_need_a_city(self):
        self.assertEqual(self.get("facilities.views.get_facilities_near", lat="34.0", lon="71.5").status_code, 200)

    def test_city_plus_coordinates_measures_from_the_visitor(self):
        response = self.get(city="Peshawar", lat="34.5", lon="72.0")
        self.assertEqual(response.json()[0]["osm_id"], "far")  # default order: nearest to the visitor

    def test_sort_by_name(self):
        response = self.get(city="Peshawar", sort="name")
        self.assertEqual([f["osm_id"] for f in response.json()], ["far", "near", "mid"])

    def test_sort_by_distance_uses_the_city_centre(self):
        response = self.get(city="Peshawar", sort="distance")
        body = response.json()
        self.assertEqual(body[0]["osm_id"], "near")
        self.assertIsNotNone(body[0]["distance_km"])

    def test_distance_is_null_without_a_reference_point(self):
        self.assertIsNone(self.get(city="Peshawar").json()[0]["distance_km"])

    def test_text_search(self):
        response = self.get(city="Peshawar", q="  clinic ")
        self.assertEqual([f["osm_id"] for f in response.json()], ["near"])
        self.assertEqual(response["X-Total-Count"], "1")

    def test_wheelchair_filter_and_field(self):
        response = self.get(city="Peshawar", wheelchair="true")
        self.assertEqual([f["osm_id"] for f in response.json()], ["far"])
        self.assertEqual(response.json()[0]["wheelchair"], "yes")

    def test_filters_are_applied_before_the_limit(self):
        response = self.get(city="Peshawar", wheelchair="true", limit="1")
        self.assertEqual([f["osm_id"] for f in response.json()], ["far"])

    def test_a_location_or_a_city_is_required(self):
        self.assertEqual(self.client.get("/api/facilities").status_code, 400)

    def test_coordinate_validation(self):
        for params in (
            {"lat": "34.0"},  # lon missing
            {"lon": "71.5"},  # lat missing
            {"lat": "abc", "lon": "71.5"},
            {"lat": "nan", "lon": "71.5"},
            {"lat": "inf", "lon": "71.5"},
            {"lat": "95", "lon": "71.5"},
            {"lat": "25.0", "lon": "67.0"},  # Karachi: outside the supported area
        ):
            response = self.client.get("/api/facilities", params)
            self.assertEqual(response.status_code, 400, params)

    def test_bad_sort_and_flags_are_rejected(self):
        self.assertEqual(self.get(city="Peshawar", sort="price").status_code, 400)
        self.assertEqual(self.get(city="Peshawar", wheelchair="maybe").status_code, 400)

    def test_very_long_queries_are_truncated_not_rejected(self):
        self.assertEqual(self.get(city="Peshawar", q="x" * 5000).status_code, 200)
