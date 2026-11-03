"""Gunicorn settings. Every value can be overridden with an environment variable."""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# The API is I/O-bound (it waits on healthsites.io / Overpass), so a handful of
# workers is plenty. Keep this small on a micro instance.
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 4)))

# A cold city can need several sequential upstream calls of up to 30 s each.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

# Log to stdout/stderr so systemd, Docker or CloudWatch collect it.
accesslog = "-"
errorlog = "-"

# Privacy: "near me" requests carry the visitor's coordinates in the query
# string (?lat=..&lon=..). Log the path only (%(U)s), never the query string.
access_log_format = '%(h)s "%(m)s %(U)s" %(s)s %(b)s %(L)s'
