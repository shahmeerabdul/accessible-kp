import logging

from rest_framework.throttling import AnonRateThrottle

logger = logging.getLogger(__name__)


class FailOpenAnonRateThrottle(AnonRateThrottle):
    """
    Per-client rate limit that keeps serving requests if the cache that stores
    the counters (e.g. Redis) is unreachable. Without this, a cache outage would
    turn every API call into a 500.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as exc:
            logger.warning("Rate-limit cache unavailable, allowing request: %s", type(exc).__name__)
            return True
