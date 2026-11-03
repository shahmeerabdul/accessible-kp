"""Data-quality clean-up: junk names, duplicate records and the type filter."""
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from facilities import services
from facilities.services import (
    clean_name,
    filter_facilities,
    merge_nearby_duplicates,
    normalize_element,
    type_group,
)


def fac(osm_id, name="", facility_type="Hospital", lat=34.0, lon=71.5, **extra):
    base = {
        "osm_id": osm_id, "name": name, "facility_type": facility_type, "address": "", "phone": "",
        "website": "", "email": "", "is_24_7": None, "is_emergency": None, "wheelchair": "",
        "ownership": "", "lat": lat, "lon": lon,
    }
    return {**base, **extra}


class CleanNameTests(SimpleTestCase):
    def test_numbers_and_punctuation_are_not_names(self):
        for junk in ("82", "103", "-", "...", "12 34", "#5", "", None, "  "):
            self.assertEqual(clean_name(junk), "", repr(junk))

    def test_real_names_are_kept_and_tidied(self):
        self.assertEqual(clean_name("HG225"), "HG225")
        self.assertEqual(clean_name("Hospital 2"), "Hospital 2")
        self.assertEqual(clean_name("  Lady   Reading  Hospital "), "Lady Reading Hospital")
        self.assertEqual(clean_name("ہسپتال"), "ہسپتال")  # Urdu letters count as letters

    def test_normalisation_applies_it(self):
        element = {"type": "node", "id": 1, "lat": 1.0, "lon": 2.0, "tags": {"name": "55", "amenity": "hospital"}}
        self.assertEqual(normalize_element(element)["name"], "")


class MergeDuplicatesTests(SimpleTestCase):
    def test_same_name_close_together_is_merged_keeping_the_most_complete(self):
        thin = fac("way/1", "Hayatabad Medical Complex", lat=34.0000, lon=71.5000)
        rich = fac("node/2", "hayatabad medical complex", lat=34.0005, lon=71.5005,  # ~70 m away
                   phone="091-111", ownership="government", is_emergency=True)
        result = merge_nearby_duplicates([thin, rich])
        self.assertEqual([f["osm_id"] for f in result], ["node/2"])

    def test_first_record_wins_a_tie(self):
        a, b = fac("a", "CMH", lat=34.0, lon=71.5), fac("b", "CMH", lat=34.0003, lon=71.5003)
        self.assertEqual([f["osm_id"] for f in merge_nearby_duplicates([a, b])], ["a"])

    def test_same_name_far_apart_is_kept(self):
        a, b = fac("a", "Civil Dispensary", lat=34.0, lon=71.5), fac("b", "Civil Dispensary", lat=34.05, lon=71.5)
        self.assertEqual(len(merge_nearby_duplicates([a, b])), 2)

    def test_different_names_close_together_are_kept(self):
        a, b = fac("a", "Alpha Clinic"), fac("b", "Beta Clinic")
        self.assertEqual(len(merge_nearby_duplicates([a, b])), 2)

    def test_unnamed_facilities_are_never_merged(self):
        self.assertEqual(len(merge_nearby_duplicates([fac("a"), fac("b")])), 2)

    def test_order_is_preserved(self):
        data = [fac("1", "A", lat=34.0), fac("2", "B", lat=34.1), fac("3", "A", lat=34.0001), fac("4", "C", lat=34.2)]
        self.assertEqual([f["osm_id"] for f in merge_nearby_duplicates(data)], ["1", "2", "4"])

    def test_duplicates_are_merged_before_caching(self):
        cache.clear()
        data = [fac("a", "CMH"), fac("b", "CMH", lat=34.0002)]
        with mock.patch.object(services, "FACILITIES_PROVIDER", "healthsites"), \
                mock.patch.object(services, "fetch_facilities_from_healthsites", return_value=data):
            first = services.get_facilities_by_city("Peshawar")
            second = services.get_facilities_by_city("Peshawar")  # from the cache
        cache.clear()
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)


class TypeGroupTests(SimpleTestCase):
    def test_grouping(self):
        self.assertEqual(type_group("Hospital"), "hospital")
        self.assertEqual(type_group("Clinic"), "clinic")
        self.assertEqual(type_group("BHU"), "health_unit")
        self.assertEqual(type_group("RHC"), "health_unit")
        self.assertEqual(type_group("Pharmacy"), "pharmacy_lab")
        self.assertEqual(type_group("Laboratory"), "pharmacy_lab")
        self.assertEqual(type_group("Alternative"), "other")
        self.assertEqual(type_group(""), "other")

    def test_filter(self):
        data = [fac("1", facility_type="Hospital"), fac("2", facility_type="Pharmacy"),
                fac("3", facility_type="BHU"), fac("4", facility_type="Alternative")]
        ids = lambda group: [f["osm_id"] for f in filter_facilities(data, type_filter=group)]  # noqa: E731
        self.assertEqual(ids("hospital"), ["1"])
        self.assertEqual(ids("pharmacy_lab"), ["2"])
        self.assertEqual(ids("health_unit"), ["3"])
        self.assertEqual(ids("other"), ["4"])
        self.assertEqual(ids(""), ["1", "2", "3", "4"])


class TypeFilterApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.data = [fac("h", "H", "Hospital"), fac("p", "P", "Pharmacy"), fac("c", "C", "Clinic")]

    def get(self, **params):
        with mock.patch("facilities.views.get_facilities_by_city", return_value=self.data):
            return self.client.get("/api/facilities", {"city": "Peshawar", **params})

    def test_type_filter(self):
        response = self.get(type="pharmacy_lab")
        self.assertEqual([f["osm_id"] for f in response.json()], ["p"])
        self.assertEqual(response["X-Total-Count"], "1")

    def test_type_is_case_insensitive_and_validated(self):
        self.assertEqual(self.get(type="HOSPITAL").status_code, 200)
        self.assertEqual(self.get(type="spa").status_code, 400)
