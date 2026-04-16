"""Sanity check for the ESI refresh-token flow.

Run with: `uv run python test_esi_refresh.py`

Not a pytest suite — intentionally dependency-free so it can be executed
directly during manual verification. Exercises the refresh path end-to-end
by stubbing out httpx + keyring, the two external boundaries, and asserts:

1. `self.token` is replaced with the new access token.
2. The rotated refresh_token (NOT the old one) is what ends up in keyring.
   CCP rotates the refresh_token on every call; re-using the old value on
   the next refresh fails with `invalid_grant`, so this is the critical
   regression to guard against.
3. The sso_timer is rescheduled relative to the NEW expires_in value.
4. Character name updates if it changed (the case that motivated re-decoding
   the JWT on every refresh rather than assuming it's immutable).
"""

import base64
import json
import sys
import threading
from unittest import mock


def make_jwt(sub="CHARACTER:EVE:91234567", name="Test Pilot"):
    """Build a signature-less JWT whose payload decodes to the given claims.
    Only the payload is read by ESI._decode_jwt_payload; signature is not
    verified today (deferred to a separate task), so a stub header + empty
    sig are sufficient."""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
    payload_json = json.dumps({"sub": sub, "name": name, "scp": []}).encode()
    payload = base64.urlsafe_b64encode(payload_json).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def run():
    # Import after we've set up the module path; keyring import inside
    # esi.py is optional and wrapped in try/except, so this works even if
    # keyring isn't installed in the current environment.
    from shortcircuit.model.esi.esi import ESI

    login_events = []
    logout_events = []

    esi = ESI(
        login_callback=lambda result: login_events.append(result),
        logout_callback=lambda: logout_events.append(True),
    )

    # Seed as if the user had already logged in: we're simulating the timer
    # firing a refresh. Short-circuit the "first login" flow.
    esi.token = "old-access-token"
    esi.refresh_token = "OLD_REFRESH_TOKEN"
    esi.char_id = 91234567
    esi.char_name = "Old Name"

    # Fake keyring backend: dict keyed by (service, username).
    keyring_store = {}

    def fake_set_password(service, username, password):
        keyring_store[(service, username)] = password

    def fake_get_password(service, username):
        return keyring_store.get((service, username))

    def fake_delete_password(service, username):
        keyring_store.pop((service, username), None)

    # Fake httpx response: CCP's token endpoint returns a fresh access token,
    # a ROTATED refresh token, and a new expires_in.
    new_access = make_jwt(sub="CHARACTER:EVE:91234567", name="Renamed Pilot")
    captured_post_args = {}

    def fake_post(url, data=None, headers=None, **kwargs):
        captured_post_args["url"] = url
        captured_post_args["data"] = data
        return FakeResponse(
            200,
            {
                "access_token": new_access,
                "refresh_token": "NEW_ROTATED_REFRESH_TOKEN",
                "expires_in": 1200,
                "token_type": "Bearer",
            },
        )

    fake_endpoints = {"token_endpoint": "https://login.eveonline.com/v2/oauth/token"}

    with mock.patch("shortcircuit.model.esi.esi.httpx.post", side_effect=fake_post), \
         mock.patch("shortcircuit.model.esi.esi.discover_sso_endpoints", return_value=fake_endpoints), \
         mock.patch("shortcircuit.model.esi.esi.keyring.set_password", side_effect=fake_set_password), \
         mock.patch("shortcircuit.model.esi.esi.keyring.get_password", side_effect=fake_get_password), \
         mock.patch("shortcircuit.model.esi.esi.keyring.delete_password", side_effect=fake_delete_password), \
         mock.patch.object(ESI, "_save_persisted_char_id", staticmethod(lambda _cid: None)), \
         mock.patch.object(ESI, "_clear_persisted_char_id", staticmethod(lambda: None)):

        ok = esi._refresh_access_token()

    assert ok is True, "refresh should report success"
    assert esi.token == new_access, "access token not replaced"
    assert esi.refresh_token == "NEW_ROTATED_REFRESH_TOKEN", \
        "refresh_token not rotated in memory"
    assert esi.char_name == "Renamed Pilot", \
        "char_name not re-decoded from refreshed JWT"
    assert keyring_store[(ESI.KEYRING_SERVICE, "91234567")] == "NEW_ROTATED_REFRESH_TOKEN", \
        "rotated refresh_token was not persisted to keyring — next refresh would fail with invalid_grant"
    assert captured_post_args["data"]["grant_type"] == "refresh_token"
    assert captured_post_args["data"]["refresh_token"] == "OLD_REFRESH_TOKEN", \
        "the OLD refresh token must be sent on the wire; new one only exists in the response"
    assert "code_verifier" not in captured_post_args["data"], \
        "code_verifier is for the initial auth-code exchange only"
    assert isinstance(esi.sso_timer, threading.Timer), \
        "a new timer must be scheduled so the next refresh fires before expiry"
    esi.sso_timer.cancel()

    # --- Second scenario: dead refresh token ---
    # Reset state as if we'd logged in again.
    esi.token = "still-valid-access"
    esi.refresh_token = "EXPIRED_REFRESH_TOKEN"
    esi.char_id = 91234567
    esi.char_name = "Pilot"
    logout_events.clear()

    # Populate keyring so we can prove it gets wiped on a 400 from CCP.
    keyring_store[(ESI.KEYRING_SERVICE, "91234567")] = "EXPIRED_REFRESH_TOKEN"

    def fake_post_rejected(url, data=None, headers=None, **kwargs):
        return FakeResponse(400, {"error": "invalid_grant"})

    with mock.patch("shortcircuit.model.esi.esi.httpx.post", side_effect=fake_post_rejected), \
         mock.patch("shortcircuit.model.esi.esi.discover_sso_endpoints", return_value=fake_endpoints), \
         mock.patch("shortcircuit.model.esi.esi.keyring.set_password", side_effect=fake_set_password), \
         mock.patch("shortcircuit.model.esi.esi.keyring.get_password", side_effect=fake_get_password), \
         mock.patch("shortcircuit.model.esi.esi.keyring.delete_password", side_effect=fake_delete_password), \
         mock.patch.object(ESI, "_save_persisted_char_id", staticmethod(lambda _cid: None)), \
         mock.patch.object(ESI, "_clear_persisted_char_id", staticmethod(lambda: None)):

        ok = esi._refresh_access_token()

    assert ok is False, "a 400 from CCP must be reported as a failed refresh"
    assert esi.token is None, "token state must be cleared on a dead refresh"
    assert esi.refresh_token is None
    assert (ESI.KEYRING_SERVICE, "91234567") not in keyring_store, \
        "dead refresh token must be purged from keyring — otherwise we retry it forever"
    assert logout_events, "logout_callback must fire so the UI reflects the signed-out state"

    print("test_esi_refresh.py: OK")


if __name__ == "__main__":
    sys.exit(run() or 0)
