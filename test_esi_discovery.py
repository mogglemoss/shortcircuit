"""
Smoke test for EVE SSO OAuth metadata discovery.

Verifies that:
  * the live metadata endpoint responds with JSON containing the two fields
    we actually consume (authorization_endpoint, token_endpoint);
  * both returned URLs still point at login.eveonline.com — sanity check so
    we don't silently follow a redirect somewhere unexpected;
  * when the HTTP call fails, discover_sso_endpoints falls back to the
    hardcoded constants rather than bubbling the error into the login flow.

Run directly:
    uv run python test_esi_discovery.py
Or via pytest:
    uv run pytest test_esi_discovery.py
"""

from unittest.mock import patch
from urllib.parse import urlparse

import httpx

from shortcircuit.model.esi import esi as esi_mod
from shortcircuit.model.esi.esi import (
    ENDPOINT_EVE_METADATA,
    FALLBACK_AUTHORIZATION_ENDPOINT,
    FALLBACK_TOKEN_ENDPOINT,
    discover_sso_endpoints,
)


def _reset_cache():
    with esi_mod._metadata_cache_lock:
        esi_mod._metadata_cache["fetched_at"] = 0.0
        esi_mod._metadata_cache["endpoints"] = None


def test_live_metadata_endpoint_returns_expected_fields():
    """CCP's metadata document must expose the two fields we consume."""
    r = httpx.get(ENDPOINT_EVE_METADATA, timeout=10.0)
    r.raise_for_status()
    data = r.json()
    assert "authorization_endpoint" in data, data
    assert "token_endpoint" in data, data
    assert urlparse(data["authorization_endpoint"]).netloc == "login.eveonline.com"
    assert urlparse(data["token_endpoint"]).netloc == "login.eveonline.com"


def test_discover_sso_endpoints_against_live_service():
    """discover_sso_endpoints returns EVE-hosted URLs on the happy path."""
    _reset_cache()
    endpoints = discover_sso_endpoints(force_refresh=True)
    assert urlparse(endpoints["authorization_endpoint"]).netloc == "login.eveonline.com"
    assert urlparse(endpoints["token_endpoint"]).netloc == "login.eveonline.com"


def test_discover_sso_endpoints_falls_back_when_request_fails():
    """If the metadata fetch raises, we must not propagate — login has to work."""
    _reset_cache()

    def _boom(*_args, **_kwargs):
        raise httpx.ConnectError("simulated network failure")

    with patch("shortcircuit.model.esi.esi.httpx.get", side_effect=_boom):
        endpoints = discover_sso_endpoints(force_refresh=True)

    assert endpoints["authorization_endpoint"] == FALLBACK_AUTHORIZATION_ENDPOINT
    assert endpoints["token_endpoint"] == FALLBACK_TOKEN_ENDPOINT


if __name__ == "__main__":
    failures = 0
    for name, fn in [
        ("live metadata endpoint shape", test_live_metadata_endpoint_returns_expected_fields),
        ("discover_sso_endpoints live", test_discover_sso_endpoints_against_live_service),
        ("fallback on network error", test_discover_sso_endpoints_falls_back_when_request_fails),
    ]:
        try:
            fn()
            print("PASS: {}".format(name))
        except Exception as e:
            failures += 1
            print("FAIL: {} -> {!r}".format(name, e))
    raise SystemExit(failures)
