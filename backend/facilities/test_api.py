import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from facilities import services
from facilities.throttling import FailOpenAnonRateThrottle

BACKEND_DIR = Path(__file__).resolve().parent.parent

PROD_ENV = {
    "DJANGO_DEBUG": "false",
    "DJANGO_SECRET_KEY": "a-long-random-unique-secret-value-for-tests-only-0123456789-abcdefghijklmnop",
    "DJANGO_ALLOWED_HOSTS": "api.example.com",
    "CORS_ALLOWED_ORIGINS": "https://app.example.com",
}


def run_django(args, **env_overrides):
    """Run a python snippet / manage.py command in a clean process with explicit settings env."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "CORS_", "REDIS_", "LOG_"))}
    env["DJANGO_SETTINGS_MODULE"] = "backend.settings"
    # Explicit (even empty) values win over anything load_dotenv() reads from a local .env.
    env.update({"DJANGO_DEBUG": "", "DJANGO_SECRET_KEY": "", "DJANGO_ALLOWED_HOSTS": "",
                "CORS_ALLOWED_ORIGINS": "", "REDIS_URL": "", "LOG_LEVEL": ""})
    env.update(env_overrides)
    return subprocess.run([sys.executable, *args], cwd=BACKEND_DIR, env=env, capture_output=True, text=True)


def read_settings(names, **env_overrides):
    code = (
        "import json; from django.conf import settings; "
        f"print(json.dumps({{n: getattr(settings, n, None) for n in {names!r}}}))"
    )
    result = run_django(["-c", code], **env_overrides)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


class HealthEndpointTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_health_returns_ok_without_touching_the_provider(self):
        with mock.patch.object(services.requests, "get") as get, mock.patch.object(services.requests, "post") as post:
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        get.assert_not_called()
        post.assert_not_called()

    def test_health_is_not_throttled(self):
        from rest_framework.throttling import AnonRateThrottle

        with mock.patch.dict(AnonRateThrottle.THROTTLE_RATES, {"anon": "2/min"}):
            codes = [self.client.get("/api/health").status_code for _ in range(5)]
        self.assertEqual(codes, [200] * 5)


class HttpsRedirectBehaviourTests(SimpleTestCase):
    """With the production redirect on, plain-HTTP requests redirect except the health check."""

    def test_http_is_redirected_but_health_check_is_not(self):
        from django.test import override_settings

        with override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^api/health$"],
                               ALLOWED_HOSTS=["testserver"]):
            client = APIClient()
            api = client.get("/api/facilities", {"city": "Peshawar"})  # plain HTTP
            health = client.get("/api/health")  # plain HTTP
            secure = client.get("/api/health", secure=True)
        self.assertEqual(api.status_code, 301)
        self.assertTrue(api["Location"].startswith("https://"))
        self.assertEqual(health.status_code, 200)
        self.assertEqual(secure.status_code, 200)


class FacilityViewValidationTests(SimpleTestCase):
    """Request validation and provider failures, as seen by an API client."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_city_is_required(self):
        response = self.client.get("/api/facilities")
        self.assertEqual(response.status_code, 400)
        self.assertIn("city", response.json()["detail"])

    def test_unsupported_city_is_rejected(self):
        response = self.client.get("/api/facilities", {"city": "Atlantis"})
        self.assertEqual(response.status_code, 400)

    def test_limit_must_be_an_integer(self):
        response = self.client.get("/api/facilities", {"city": "Peshawar", "limit": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_limit_is_clamped(self):
        data = [
            {"osm_id": f"node/{i}", "name": "", "facility_type": "", "address": "", "phone": "", "website": "",
             "email": "", "is_24_7": None, "is_emergency": None, "ownership": "", "lat": 34.0, "lon": 71.5}
            for i in range(10)
        ]
        with mock.patch("facilities.views.get_facilities_by_city", return_value=data):
            zero = self.client.get("/api/facilities", {"city": "Peshawar", "limit": "0"})
            huge = self.client.get("/api/facilities", {"city": "Peshawar", "limit": "99999"})
        self.assertEqual(len(zero.json()), 1)  # clamped up to 1
        self.assertEqual(len(huge.json()), 10)  # clamped down to the cap, all 10 returned

    def test_provider_failure_is_a_502(self):
        with mock.patch("facilities.views.get_facilities_by_city", side_effect=services.FacilityProviderError("down")):
            response = self.client.get("/api/facilities", {"city": "Peshawar"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "down"})


class CacheOutageTests(SimpleTestCase):
    """A dead shared cache (Redis) must degrade the API, not crash it."""

    def setUp(self):
        self.client = APIClient()

    @staticmethod
    def dead_cache():
        broken = mock.Mock()
        broken.get.side_effect = ConnectionError("redis is down")
        broken.set.side_effect = ConnectionError("redis is down")
        return broken

    def test_api_still_works_when_the_cache_is_down(self):
        data = [{"osm_id": "node/1", "name": "A", "facility_type": "Hospital", "address": "", "phone": "",
                 "website": "", "email": "", "is_24_7": None, "is_emergency": None, "ownership": "",
                 "lat": 34.0, "lon": 71.5}]
        # Both users of the cache are broken: the result cache and the throttle counters.
        with mock.patch.object(services, "cache", self.dead_cache()), \
                mock.patch.object(SimpleRateThrottle, "cache", self.dead_cache()), \
                mock.patch.object(services, "FACILITIES_PROVIDER", "healthsites"), \
                mock.patch.object(services, "fetch_facilities_from_healthsites", return_value=data) as fetch:
            response = self.client.get("/api/facilities", {"city": "Peshawar"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        fetch.assert_called_once()

    def test_throttle_fails_open_when_the_cache_is_down(self):
        with mock.patch.object(AnonRateThrottle, "allow_request", side_effect=ConnectionError("redis is down")):
            self.assertTrue(FailOpenAnonRateThrottle().allow_request(mock.Mock(), mock.Mock()))

    def test_throttle_still_limits_when_the_cache_works(self):
        cache.clear()
        with mock.patch.dict(AnonRateThrottle.THROTTLE_RATES, {"anon": "1/min"}):
            codes = [self.client.get("/api/facilities").status_code for _ in range(2)]
        self.assertEqual(codes, [400, 429])
        cache.clear()


class SharedCacheSettingsTests(SimpleTestCase):
    def test_in_memory_cache_is_the_default(self):
        caches = read_settings(["CACHES"], DJANGO_DEBUG="true")["CACHES"]
        self.assertTrue(caches["default"]["BACKEND"].endswith("LocMemCache"))

    def test_redis_url_switches_to_the_shared_cache(self):
        caches = read_settings(["CACHES"], DJANGO_DEBUG="true", REDIS_URL="redis://cache.example:6379/0")["CACHES"]
        self.assertTrue(caches["default"]["BACKEND"].endswith("RedisCache"))
        self.assertEqual(caches["default"]["LOCATION"], "redis://cache.example:6379/0")


class LoggingSettingsTests(SimpleTestCase):
    def test_logs_go_to_the_console_at_info_by_default(self):
        logging_cfg = read_settings(["LOGGING"], DJANGO_DEBUG="true")["LOGGING"]
        self.assertEqual(logging_cfg["root"]["level"], "INFO")
        self.assertEqual(logging_cfg["root"]["handlers"], ["console"])

    def test_log_level_is_configurable(self):
        logging_cfg = read_settings(["LOGGING"], DJANGO_DEBUG="true", LOG_LEVEL="debug")["LOGGING"]
        self.assertEqual(logging_cfg["root"]["level"], "DEBUG")


class ProductionSecuritySettingsTests(SimpleTestCase):
    NAMES = ["SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_HSTS_SECONDS",
             "SECURE_PROXY_SSL_HEADER", "SECURE_REDIRECT_EXEMPT"]

    def test_https_hardening_is_on_in_production(self):
        s = read_settings(self.NAMES, **PROD_ENV)
        self.assertTrue(s["SECURE_SSL_REDIRECT"])
        self.assertTrue(s["SESSION_COOKIE_SECURE"])
        self.assertTrue(s["CSRF_COOKIE_SECURE"])
        self.assertGreater(s["SECURE_HSTS_SECONDS"], 0)
        self.assertEqual(s["SECURE_PROXY_SSL_HEADER"], ["HTTP_X_FORWARDED_PROTO", "https"])

    def test_health_check_is_exempt_from_the_https_redirect(self):
        self.assertIn(r"^api/health$", read_settings(self.NAMES, **PROD_ENV)["SECURE_REDIRECT_EXEMPT"])

    def test_https_hardening_is_off_in_local_development(self):
        s = read_settings(self.NAMES, DJANGO_DEBUG="true")
        self.assertFalse(s["SECURE_SSL_REDIRECT"])
        self.assertFalse(s["SESSION_COOKIE_SECURE"])

    def test_can_opt_out_of_proxy_header_and_redirect(self):
        s = read_settings(self.NAMES, **PROD_ENV, DJANGO_BEHIND_PROXY="false", DJANGO_SECURE_SSL_REDIRECT="false")
        self.assertIsNone(s["SECURE_PROXY_SSL_HEADER"])
        self.assertFalse(s["SECURE_SSL_REDIRECT"])

    def test_django_deploy_check_has_no_errors(self):
        result = run_django(["manage.py", "check", "--deploy"], **PROD_ENV)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
