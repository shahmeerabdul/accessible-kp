import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle

from facilities import services

BACKEND_DIR = Path(__file__).resolve().parent.parent
FAKE_KEY = "FAKE-TEST-KEY-123"


class ApiTestCase(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()


class ErrorMessagesDoNotLeakKeyTests(ApiTestCase):
    """Issue #1: upstream failures must not expose the API key to clients."""

    def _failing_get(self, *args, **kwargs):
        # Mimics real `requests` errors, whose text includes the full URL.
        raise requests.ConnectionError(
            f"HTTPSConnectionPool: Max retries exceeded with url: "
            f"/api/v3/facilities/?api-key={FAKE_KEY}&page=1"
        )

    def test_healthsites_connection_error_is_generic(self):
        with mock.patch.object(services, "FACILITIES_PROVIDER", "healthsites"), \
                mock.patch.object(services, "HEALTHSITES_API_KEY", FAKE_KEY), \
                mock.patch.object(services.requests, "get", self._failing_get):
            response = self.client.get("/api/facilities", {"city": "Peshawar"})

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(FAKE_KEY, response.content.decode())
        self.assertNotIn("api-key", response.content.decode())

    def test_overpass_connection_error_is_generic(self):
        def failing_post(*args, **kwargs):
            raise requests.ConnectionError("failed for url http://secret.example/path?token=abc")

        with mock.patch.object(services, "FACILITIES_PROVIDER", "overpass"), \
                mock.patch.object(services.requests, "post", failing_post):
            response = self.client.get("/api/facilities", {"city": "Peshawar"})

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret.example", response.content.decode())
        self.assertNotIn("token=abc", response.content.decode())


class RateLimitTests(ApiTestCase):
    """Issue #3: the API is throttled per client."""

    def test_exceeding_the_limit_returns_429(self):
        with mock.patch.dict(AnonRateThrottle.THROTTLE_RATES, {"anon": "2/min"}):
            codes = [self.client.get("/api/facilities").status_code for _ in range(3)]

        # The first two are within the limit (400: missing city); the third is throttled.
        self.assertEqual(codes, [400, 400, 429])


class AdminRemovedTests(ApiTestCase):
    """Issue #4: the Django admin is not exposed."""

    def test_admin_returns_404(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)
        self.assertEqual(self.client.get("/admin/login/").status_code, 404)


class SettingsHardeningTests(SimpleTestCase):
    """Issue #2: settings refuse insecure configuration outside DEBUG."""

    def _import_settings(self, **overrides):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "CORS_"))}
        env["DJANGO_SETTINGS_MODULE"] = "backend.settings"
        # Explicit values (even empty) win over anything load_dotenv() reads from .env.
        env.update(
            {
                "DJANGO_DEBUG": "",
                "DJANGO_SECRET_KEY": "",
                "DJANGO_ALLOWED_HOSTS": "",
                "CORS_ALLOWED_ORIGINS": "",
            }
        )
        env.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", "import backend.settings"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    PROD = {
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": "a-long-random-unique-secret-value-for-tests-only-0123456789",
        "DJANGO_ALLOWED_HOSTS": "api.example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
    }

    def test_valid_production_config_loads(self):
        result = self._import_settings(**self.PROD)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_secret_key_is_rejected(self):
        result = self._import_settings(**{**self.PROD, "DJANGO_SECRET_KEY": ""})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_placeholder_secret_key_is_rejected(self):
        result = self._import_settings(**{**self.PROD, "DJANGO_SECRET_KEY": "change-me-in-production"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_wildcard_allowed_hosts_is_rejected(self):
        result = self._import_settings(**{**self.PROD, "DJANGO_ALLOWED_HOSTS": "*"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_ALLOWED_HOSTS", result.stderr)

    def test_missing_cors_origins_is_rejected(self):
        result = self._import_settings(**{**self.PROD, "CORS_ALLOWED_ORIGINS": ""})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CORS_ALLOWED_ORIGINS", result.stderr)

    def test_debug_is_off_unless_explicitly_true(self):
        # DEBUG not enabled and nothing else configured: must not start.
        result = self._import_settings()
        self.assertNotEqual(result.returncode, 0)

    def test_local_debug_config_loads(self):
        result = self._import_settings(DJANGO_DEBUG="true")
        self.assertEqual(result.returncode, 0, result.stderr)
