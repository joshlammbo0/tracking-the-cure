"""Shared HTTP session with retries, polite rate limiting, and a contact User-Agent."""
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "TrackingTheCure research-tracker contact@example.com",
)

_session = None
_last_call = {}


def session():
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(total=4, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=("GET", "HEAD"))
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = USER_AGENT
        _session = s
    return _session


def get(url, params=None, min_interval=0.0, key=None, **kw):
    """GET with a per-host minimum interval (PubMed allows 3 req/s, SEC 10 req/s)."""
    key = key or url.split("/")[2]
    wait = _last_call.get(key, 0) + min_interval - time.time()
    if wait > 0:
        time.sleep(wait)
    try:
        r = session().get(url, params=params, timeout=kw.pop("timeout", 30), **kw)
    finally:
        _last_call[key] = time.time()
    r.raise_for_status()
    return r
