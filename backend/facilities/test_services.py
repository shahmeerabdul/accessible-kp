import itertools
import math
import re
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from facilities import services
from facilities.services import (
    FETCH_CAP,
    build_overpass_query,
    dedupe_facilities,
    filter_facilities,
    healthsites_attrs_to_tags,
    infer_facility_type,
    infer_ownership,
    is_supported_city,
    normalize_element,
    normalize_healthsites_record,
)


def fac(osm_id, ownership="", emergency=None, open_24_7=None, name="x"):
    return {
        "osm_id": osm_id,
        "name": name,
        "facility_type": "Hospital",
        "address": "",
        "phone": "",
        "website": "",
        "email": "",
        "is_24_7": open_24_7,
        "is_emergency": emergency,
        "ownership": ownership,
        "lat": 34.0,
        "lon": 71.5,
    }


class FacilityTypeTests(SimpleTestCase):
    """Issue #7"""

    def test_bhu_and_rhc_as_whole_words(self):
        self.assertEqual(infer_facility_type({"name": "Jamrud BHU"}), "BHU")
        self.assertEqual(infer_facility_type({"name": "BHU-Shahkas"}), "BHU")
        self.assertEqual(infer_facility_type({"name": "Basic Health Unit Tangi"}), "BHU")
        self.assertEqual(infer_facility_type({"name": "RHC Tangi"}), "RHC")
        self.assertEqual(infer_facility_type({"name": "Rural Health Centre Daggar"}), "RHC")

    def test_letters_inside_other_words_do_not_match(self):
        self.assertEqual(infer_facility_type({"name": "Abhuman Clinic", "amenity": "clinic"}), "Clinic")
        self.assertEqual(infer_facility_type({"name": "Sarhcare Clinic", "amenity": "clinic"}), "Clinic")

    def test_overpass_query_fetches_healthcare_doctor(self):
        query = build_overpass_query((34.0151, 71.5249))
        self.assertIn("hospital|clinic|centre|doctor", query)
        self.assertIn(f"out center {FETCH_CAP};", query)

    def test_healthcare_doctor_is_a_clinic(self):
        self.assertEqual(infer_facility_type({"healthcare": "doctor"}), "Clinic")


class OwnershipTests(SimpleTestCase):
    """Issue #8"""

    def test_clinic_or_trust_alone_is_not_private(self):
        self.assertEqual(infer_ownership({"operator": "City Clinic"}), "")
        self.assertEqual(infer_ownership({"operator": "Al-Khidmat Trust"}), "")

    def test_explicit_tags(self):
        self.assertEqual(infer_ownership({"operator": "Pvt. Ltd"}), "private")
        self.assertEqual(infer_ownership({"operator:type": "private"}), "private")
        self.assertEqual(infer_ownership({"operator:type": "government"}), "government")
        self.assertEqual(infer_ownership({"operator": "Health Department KP"}), "government")

    def test_government_markers_in_name(self):
        for name in ("DHQ Hospital Mardan", "THQ Hospital Takht Bhai", "BHU Jamrud",
                     "RHC Tangi", "Civil Hospital Bannu", "Govt. Dispensary"):
            self.assertEqual(infer_ownership({"name": name}), "government", name)

    def test_unknown_stays_unknown(self):
        self.assertEqual(infer_ownership({"name": "Sahibzada Homeopathic Clinic"}), "")
        self.assertEqual(infer_ownership({}), "")

    def test_explicit_tag_beats_name(self):
        self.assertEqual(infer_ownership({"name": "Govt Pharmacy", "operator": "Private"}), "private")


class EmailMappingTests(SimpleTestCase):
    """Issue #9"""

    def test_email_attributes_are_mapped(self):
        self.assertEqual(healthsites_attrs_to_tags({"email": "a@b.pk"})["email"], "a@b.pk")
        self.assertEqual(healthsites_attrs_to_tags({"contact_email": "c@d.pk"})["email"], "c@d.pk")

    def test_email_reaches_the_normalized_record(self):
        record = {
            "osm_id": 1,
            "osm_type": "node",
            "centroid": {"coordinates": [71.5, 34.0]},
            "attributes": {"name": "X", "email": "a@b.pk"},
        }
        self.assertEqual(normalize_healthsites_record(record)["email"], "a@b.pk")


class UniqueIdTests(SimpleTestCase):
    """Issue #10"""

    def test_overpass_ids_include_the_element_type(self):
        base = {"lat": 1.0, "lon": 2.0, "tags": {"name": "A"}}
        node = normalize_element({**base, "type": "node", "id": 5})
        way = normalize_element({**base, "type": "way", "id": 5})
        self.assertEqual((node["osm_id"], way["osm_id"]), ("node/5", "way/5"))

    def test_healthsites_ids_include_the_osm_type(self):
        record = {"osm_id": 7, "osm_type": "way", "centroid": {"coordinates": [71.5, 34.0]}, "attributes": {}}
        self.assertEqual(normalize_healthsites_record(record)["osm_id"], "way/7")

    def test_dedupe_keeps_first_occurrence_in_order(self):
        items = [fac("node/1", name="first"), fac("node/2"), fac("node/1", name="dupe")]
        result = dedupe_facilities(items)
        self.assertEqual([f["osm_id"] for f in result], ["node/1", "node/2"])
        self.assertEqual(result[0]["name"], "first")


class CityListTests(SimpleTestCase):
    """Issue #11"""

    def test_swat_removed_mingora_kept(self):
        self.assertFalse(is_supported_city("Swat"))
        self.assertTrue(is_supported_city("Mingora"))
        self.assertNotIn("swat", services.CITY_COORDINATES)


class CityCatalogueTests(SimpleTestCase):
    """The city list: consistent with the frontend, sensible and not redundant."""

    FRONTEND_CITIES = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "cities.js"

    def test_frontend_list_matches_backend(self):
        frontend = re.findall(r'"([^"]+)"', self.FRONTEND_CITIES.read_text(encoding="utf-8"))
        self.assertEqual(frontend, services.SUPPORTED_CITIES)

    def test_lookups_are_case_insensitive(self):
        self.assertTrue(is_supported_city("dera ismail khan"))
        self.assertEqual(services.get_city_center(" PESHAWAR "), services.CITY_CENTERS["Peshawar"])

    def test_all_centers_are_inside_kpk(self):
        # Rough bounding box of Khyber Pakhtunkhwa.
        for name, (lat, lon) in services.CITY_CENTERS.items():
            self.assertTrue(31.0 <= lat <= 36.9 and 69.0 <= lon <= 74.2, name)

    def test_no_two_cities_are_nearly_the_same_place(self):
        def km(a, b):
            (lat1, lon1), (lat2, lon2) = a, b
            dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
            h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
            return 12742 * math.asin(math.sqrt(h))

        for (a, ca), (b, cb) in itertools.combinations(services.CITY_CENTERS.items(), 2):
            self.assertGreater(km(ca, cb), 5, f"{a} and {b} are too close together")


class CachingTests(SimpleTestCase):
    """Issue #12: a city is fetched once, whatever the filters or limit."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_city_is_fetched_once(self):
        with mock.patch.object(services, "FACILITIES_PROVIDER", "healthsites"), \
                mock.patch.object(services, "fetch_facilities_from_healthsites", return_value=[fac("node/1")]) as fetch:
            services.get_facilities_by_city("Peshawar")
            services.get_facilities_by_city("Peshawar")
            services.get_facilities_by_city("peshawar ")
        self.assertEqual(fetch.call_count, 1)


class FilterTests(SimpleTestCase):
    """Issue #5 (service level)"""

    DATA = [
        fac("1", ownership="government", emergency=True),
        fac("2", ownership="private", emergency=True, open_24_7=True),
        fac("3", ownership="government"),
        fac("4"),
    ]

    def ids(self, **kwargs):
        return [f["osm_id"] for f in filter_facilities(self.DATA, **kwargs)]

    def test_no_filters_returns_everything(self):
        self.assertEqual(self.ids(), ["1", "2", "3", "4"])

    def test_each_filter(self):
        self.assertEqual(self.ids(ownership="government"), ["1", "3"])
        self.assertEqual(self.ids(emergency_only=True), ["1", "2"])
        self.assertEqual(self.ids(open_24_7_only=True), ["2"])

    def test_filters_combine(self):
        self.assertEqual(self.ids(ownership="government", emergency_only=True), ["1"])


class FacilityApiTests(SimpleTestCase):
    """Issues #5 and #6 (API level), with the provider mocked."""

    def setUp(self):
        self.client = APIClient()
        # 120 facilities; every 10th is an emergency facility (12 in total).
        self.data = [fac(f"node/{i}", emergency=(i % 10 == 0) or None) for i in range(120)]

    def get(self, data=None, **params):
        with mock.patch("facilities.views.get_facilities_by_city", return_value=self.data if data is None else data):
            return self.client.get("/api/facilities", {"city": "Peshawar", **params})

    def test_filter_applies_before_the_limit(self):
        # The 12 emergency facilities sit at indices 0, 10, 20 ... 110. With a
        # limit of 5 and client-side filtering only the first one would be found.
        response = self.get(emergency="true", limit="5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)
        self.assertTrue(all(f["is_emergency"] for f in response.json()))
        self.assertEqual(response["X-Total-Count"], "12")

    def test_total_count_header_and_limit(self):
        response = self.get(limit="50")
        self.assertEqual(len(response.json()), 50)
        self.assertEqual(response["X-Total-Count"], "120")
        self.assertEqual(response["X-Upstream-Capped"], "false")

    def test_upstream_capped_header(self):
        full = [fac(f"node/{i}") for i in range(FETCH_CAP)]
        response = self.get(data=full, limit="10")
        self.assertEqual(response["X-Upstream-Capped"], "true")

    def test_bad_filter_values_are_rejected(self):
        self.assertEqual(self.get(ownership="nonsense").status_code, 400)
        self.assertEqual(self.get(emergency="maybe").status_code, 400)
        self.assertEqual(self.get(open_24_7="2").status_code, 400)

    def test_ownership_filter(self):
        data = [fac("a", ownership="government"), fac("b", ownership="private")]
        response = self.get(data=data, ownership="private")
        self.assertEqual([f["osm_id"] for f in response.json()], ["b"])
