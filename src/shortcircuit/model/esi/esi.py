# esi.py

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import uuid
import webbrowser

import httpx
from appdirs import AppDirs

from shortcircuit.model.logger import Logger
from shortcircuit import USER_AGENT, __appslug__, __version__

from .server import AuthHandler, StoppableHTTPServer

try:
    import keyring
    import keyring.errors as keyring_errors
except Exception:  # pragma: no cover - keyring is an optional backend
    keyring = None
    keyring_errors = None


# CCP recommends discovering SSO endpoints from the OAuth metadata document
# rather than hardcoding them. When they retire or move a route (as with the
# 24 March 2026 spring cleaning that removed /verify and implicit flow) a
# deployed client that follows the metadata will keep working without a
# rebuild. The fallback URLs below are only used if the metadata fetch fails.
# https://developers.eveonline.com/docs/services/sso/
ENDPOINT_EVE_METADATA = "https://login.eveonline.com/.well-known/oauth-authorization-server"
FALLBACK_AUTHORIZATION_ENDPOINT = "https://login.eveonline.com/v2/oauth/authorize"
FALLBACK_TOKEN_ENDPOINT = "https://login.eveonline.com/v2/oauth/token"
_METADATA_CACHE_TTL_SECONDS = 3600

_metadata_cache_lock = threading.Lock()
_metadata_cache = {"fetched_at": 0.0, "endpoints": None}


def discover_sso_endpoints(force_refresh=False):
    """
    Fetch and cache the EVE SSO OAuth metadata document.

    Returns a dict with at least ``authorization_endpoint`` and
    ``token_endpoint``. On network failure, returns the hardcoded fallback
    values so login still works (at least until CCP retires those routes).
    The cache is per-process, in-memory, and refreshes hourly.
    """
    now = time.monotonic()
    with _metadata_cache_lock:
        cached = _metadata_cache["endpoints"]
        if (
            not force_refresh
            and cached is not None
            and now - _metadata_cache["fetched_at"] < _METADATA_CACHE_TTL_SECONDS
        ):
            return cached

    try:
        r = httpx.get(ENDPOINT_EVE_METADATA, headers={"User-Agent": USER_AGENT}, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        endpoints = {
            "authorization_endpoint": data["authorization_endpoint"],
            "token_endpoint": data["token_endpoint"],
        }
    except (httpx.HTTPError, KeyError, ValueError) as e:
        Logger.warning(
            "SSO metadata discovery failed ({}); falling back to hardcoded endpoints".format(e)
        )
        endpoints = {
            "authorization_endpoint": FALLBACK_AUTHORIZATION_ENDPOINT,
            "token_endpoint": FALLBACK_TOKEN_ENDPOINT,
        }

    with _metadata_cache_lock:
        _metadata_cache["fetched_at"] = now
        _metadata_cache["endpoints"] = endpoints
    return endpoints


class ESI:
    ENDPOINT_ESI_LOCATION_FORMAT = "https://esi.evetech.net/latest/characters/{}/location/"
    ENDPOINT_ESI_UNIVERSE_NAMES = "https://esi.evetech.net/latest/universe/names/"
    ENDPOINT_ESI_UI_WAYPOINT = "https://esi.evetech.net/latest/ui/autopilot/waypoint/"

    CLIENT_CALLBACK = "http://127.0.0.1:7444/callback/"
    CLIENT_ID = "d802bba44b7c4f6cbfa2944b0e5ea83f"
    CLIENT_SCOPES = [
        "esi-location.read_location.v1",
        "esi-ui.write_waypoint.v1",
    ]

    # Keyring service name for the persisted refresh token. Username is the
    # EVE character_id as a string, so a future multi-character feature can
    # store one entry per character without changing the schema.
    KEYRING_SERVICE = "shortcircuit-esi"
    # Filename under appdirs.user_data_dir holding the most-recently-used
    # character_id. The id itself is public (it appears in killboards, zKill,
    # ESI URLs); the secret is the refresh token, which lives in the keyring.
    CHAR_ID_META_FILENAME = "esi_char_id"
    # Refresh this many seconds before the access token actually expires, so
    # the network round-trip has slack and a brief outage doesn't drop us.
    REFRESH_BUFFER_SECONDS = 60

    def __init__(self, login_callback, logout_callback):
        self.login_callback = login_callback
        self.logout_callback = logout_callback
        self.httpd = None
        self.state = None
        self.code_verifier = None

        # Guards token state against the race between the background sso_timer
        # firing a refresh and the UI thread invoking logout().
        self._lock = threading.Lock()
        self.token = None
        self.refresh_token = None
        self.char_id = None
        self.char_name = None
        self.sso_timer = None

    @staticmethod
    def _generate_pkce():
        verifier = secrets.token_urlsafe(96)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    @staticmethod
    def _decode_jwt_payload(token):
        """
        Decode the claims from an EVE SSO JWT access token without signature
        verification. We trust the token because we just received it over TLS
        directly from login.eveonline.com's token endpoint.

        CCP removed the /verify REST endpoint on 24 March 2026 and explicitly
        recommends offline JWT decoding:
        https://developers.eveonline.com/blog/spring-cleaning-legacy-routes-removed-24-march-2026

        Relevant claims:
          sub:  "CHARACTER:EVE:<character_id>"
          name: character name
          scp:  list of granted scopes
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed JWT")
        payload_b64 = parts[1]
        # Pad for urlsafe_b64decode
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
        return payload

    def start_server(self):
        if not self.httpd:
            # Server not running - restart it
            Logger.debug("Starting server")
            self.httpd = StoppableHTTPServer(
                server_address=("127.0.0.1", 7444),
                request_handler_class=AuthHandler,
                timeout_callback=self.timeout_server,
            )
            server_thread = threading.Thread(
                target=self.httpd.serve,
                args=(self.handle_login,),
            )
            server_thread.daemon = True
            server_thread.start()
            self.state = str(uuid.uuid4())
        else:
            # Server already running - reset timeout counter
            self.httpd.tries = 0

        self.code_verifier, code_challenge = self._generate_pkce()
        endpoints = discover_sso_endpoints()
        query = urllib.parse.urlencode({
            "response_type": "code",
            "redirect_uri": ESI.CLIENT_CALLBACK,
            "client_id": ESI.CLIENT_ID,
            "scope": " ".join(ESI.CLIENT_SCOPES),
            "state": self.state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
        endpoint_auth = "{}?{}".format(endpoints["authorization_endpoint"], query)

        if __import__("sys").platform == "linux":
            import subprocess
            import os

            env = os.environ.copy()
            env.pop("LD_LIBRARY_PATH", None)
            try:
                subprocess.Popen(["xdg-open", endpoint_auth], env=env)
                return True
            except OSError:
                return webbrowser.open(endpoint_auth)
        else:
            return webbrowser.open(endpoint_auth)

    def timeout_server(self):
        self.httpd = None

    def stop_server(self):
        Logger.debug("Stopping server")
        if self.httpd:
            self.httpd.stop()
            self.httpd = None

    def handle_login(self, message):
        if not message:
            return

        if "state" in message:
            if message["state"][0] != self.state:
                Logger.warning("OAUTH state mismatch")
                return

        if "code" not in message:
            return

        # Exchange auth code for access token (PKCE flow). Reuse the metadata
        # cache warmed by start_server() so we post to the same token endpoint
        # CCP currently advertises.
        endpoints = discover_sso_endpoints()
        r = httpx.post(
            endpoints["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": message["code"][0],
                "client_id": ESI.CLIENT_ID,
                "code_verifier": self.code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if r.status_code == httpx.codes.OK:
            token_data = r.json()
            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token")
            expires_in = int(token_data["expires_in"])

            # Decode character info from the JWT access token. CCP removed the
            # /verify REST endpoint on 24 March 2026 in favour of offline JWT
            # decoding.
            try:
                claims = self._decode_jwt_payload(access_token)
                sub = claims.get("sub", "")
                # sub looks like "CHARACTER:EVE:12345"
                char_id = int(sub.rsplit(":", 1)[-1])
                char_name = str(claims.get("name", "Unknown"))
            except (ValueError, KeyError, IndexError) as e:
                Logger.warning("Failed to decode JWT claims: {}".format(e))
                self._reset_auth()
                self.login_callback({"is_ok": False, "char_name": None, "char_id": 0})
                self.stop_server()
                return

            with self._lock:
                self.token = access_token
                self.refresh_token = refresh_token
                self.char_id = char_id
                self.char_name = char_name
                self._schedule_refresh_locked(expires_in)

            if refresh_token:
                ESI._store_refresh_token(char_id, refresh_token)
                ESI._save_persisted_char_id(char_id)

            self.login_callback(
                {"is_ok": True, "char_name": char_name, "char_id": char_id}
            )
        else:
            Logger.warning("Token exchange failed: {} {}".format(r.status_code, r.text))
            self._reset_auth()
            self.login_callback({"is_ok": False, "char_name": None, "char_id": 0})

        self.stop_server()

    def _reset_auth(self):
        with self._lock:
            self.token = None
            self.refresh_token = None
            self.char_id = None
            self.char_name = None
            if self.sso_timer:
                self.sso_timer.cancel()
            self.sso_timer = None

    # ----- Refresh-token persistence -----
    #
    # The refresh token is functionally equivalent to a password — anyone
    # holding it can act as the user against ESI within the granted scopes
    # until it is revoked. We therefore store it in the OS keychain (Keychain
    # on macOS, Credential Manager on Windows, Secret Service on Linux) via
    # the `keyring` library, never in a plaintext file. If no keyring backend
    # is available (eg. a headless Linux desktop without Secret Service) we
    # silently degrade to the old behaviour: the user has to re-auth each
    # session, but we never write the secret to disk in the clear.

    @staticmethod
    def _char_id_meta_path():
        app_dirs = AppDirs(__appslug__, "mogglemoss", version=__version__)
        os.makedirs(app_dirs.user_data_dir, exist_ok=True)
        return os.path.join(app_dirs.user_data_dir, ESI.CHAR_ID_META_FILENAME)

    @staticmethod
    def _load_persisted_char_id():
        try:
            with open(ESI._char_id_meta_path(), "r") as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError, OSError):
            return None

    @staticmethod
    def _save_persisted_char_id(char_id):
        try:
            with open(ESI._char_id_meta_path(), "w") as f:
                f.write(str(char_id))
        except OSError as e:
            Logger.warning("Failed to persist char_id: {}".format(e))

    @staticmethod
    def _clear_persisted_char_id():
        try:
            os.remove(ESI._char_id_meta_path())
        except FileNotFoundError:
            pass
        except OSError as e:
            Logger.warning("Failed to clear persisted char_id: {}".format(e))

    @staticmethod
    def _store_refresh_token(char_id, refresh_token):
        if keyring is None:
            Logger.warning(
                "keyring unavailable; skipping refresh-token persistence "
                "(user will need to re-auth next session)"
            )
            return False
        try:
            keyring.set_password(ESI.KEYRING_SERVICE, str(char_id), refresh_token)
            return True
        except Exception as e:
            Logger.warning("Could not store refresh token in keyring: {}".format(e))
            return False

    @staticmethod
    def _load_refresh_token(char_id):
        if keyring is None:
            return None
        try:
            return keyring.get_password(ESI.KEYRING_SERVICE, str(char_id))
        except Exception as e:
            Logger.warning("Could not load refresh token from keyring: {}".format(e))
            return None

    @staticmethod
    def _delete_refresh_token(char_id):
        if keyring is None:
            return
        try:
            keyring.delete_password(ESI.KEYRING_SERVICE, str(char_id))
        except Exception as e:
            # PasswordDeleteError when entry doesn't exist is benign; other
            # errors we just log — there's nothing the user can do.
            if keyring_errors and isinstance(e, keyring_errors.PasswordDeleteError):
                return
            Logger.warning("Could not delete refresh token from keyring: {}".format(e))

    # ----- Refresh flow -----

    def _schedule_refresh_locked(self, expires_in):
        """Reset sso_timer to fire a refresh shortly before the access token
        expires. Caller must hold self._lock."""
        if self.sso_timer:
            self.sso_timer.cancel()
        delay = max(int(expires_in) - ESI.REFRESH_BUFFER_SECONDS, 1)
        self.sso_timer = threading.Timer(delay, self._refresh_access_token)
        self.sso_timer.daemon = True
        self.sso_timer.start()

    def _refresh_access_token(self):
        """
        Exchange the stored refresh token for a fresh access token. Called
        both at startup (to silently resume a previous session) and from the
        background sso_timer ~60s before the current access token expires.

        CCP rotates the refresh token on every successful refresh, so the
        response carries a NEW refresh_token that supersedes the old one.
        Persisting the rotated value is mandatory — re-using the old token a
        second time fails with `invalid_grant`.

        Returns True if the refresh succeeded and self.token is now valid,
        False otherwise (in which case _logout has already been invoked).
        """
        with self._lock:
            refresh_token = self.refresh_token
            char_id = self.char_id

        if not refresh_token:
            self._logout()
            return False

        # Reuse the discovered token endpoint so the refresh path survives
        # the same URL rotations the metadata discovery refactor protects
        # the initial login against.
        endpoints = discover_sso_endpoints()
        try:
            r = httpx.post(
                endpoints["token_endpoint"],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": ESI.CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as e:
            # Network blip, not necessarily a dead token. Log out so the user
            # sees an honest disconnected state; they can click Login to retry.
            Logger.warning("Refresh request failed: {}".format(e))
            self._logout()
            return False

        if r.status_code != httpx.codes.OK:
            # Refresh token is dead (revoked, expired, scope-changed). Purge
            # storage so we don't keep retrying a bad token on every startup.
            Logger.warning("Token refresh rejected: {} {}".format(r.status_code, r.text))
            if char_id is not None:
                ESI._delete_refresh_token(char_id)
            ESI._clear_persisted_char_id()
            self._logout()
            return False

        token_data = r.json()
        new_access = token_data["access_token"]
        # Defensive: spec says refresh_token is always returned on rotation,
        # but fall back to the old one if a future server omits it.
        new_refresh = token_data.get("refresh_token", refresh_token)
        expires_in = int(token_data["expires_in"])

        try:
            claims = self._decode_jwt_payload(new_access)
            sub = claims.get("sub", "")
            new_char_id = int(sub.rsplit(":", 1)[-1])
            new_char_name = str(claims.get("name", "Unknown"))
        except (ValueError, KeyError, IndexError) as e:
            Logger.warning("Refresh succeeded but JWT decode failed: {}".format(e))
            if char_id is not None:
                ESI._delete_refresh_token(char_id)
            ESI._clear_persisted_char_id()
            self._logout()
            return False

        with self._lock:
            # User may have hit Logout while httpx was in flight — don't
            # resurrect a session they explicitly killed.
            if self.refresh_token is None and self.token is None and self.char_id is None:
                Logger.debug("Discarding refresh result; logout occurred mid-flight")
                return False
            self.token = new_access
            self.refresh_token = new_refresh
            self.char_id = new_char_id
            self.char_name = new_char_name
            self._schedule_refresh_locked(expires_in)

        ESI._store_refresh_token(new_char_id, new_refresh)
        ESI._save_persisted_char_id(new_char_id)

        Logger.info("ESI access token refreshed (expires in {}s)".format(expires_in))
        return True

    def try_silent_login(self):
        """Resume a previous session using a stored refresh token, with no
        browser interaction. Intended to be called once at app startup. Fires
        login_callback on success so the UI can flip to its logged-in state.
        Returns True iff a session was resumed."""
        char_id = ESI._load_persisted_char_id()
        if char_id is None:
            return False
        refresh_token = ESI._load_refresh_token(char_id)
        if not refresh_token:
            # Stale meta file pointing at a char with no keyring entry —
            # clean it up so we don't keep checking.
            ESI._clear_persisted_char_id()
            return False

        with self._lock:
            self.refresh_token = refresh_token
            self.char_id = char_id

        if not self._refresh_access_token():
            return False

        self.login_callback({
            "is_ok": True,
            "char_name": self.char_name,
            "char_id": self.char_id,
        })
        return True

    def _get_headers(self):
        return {
            "User-Agent": USER_AGENT,
            "Authorization": "Bearer {}".format(self.token),
        }

    def get_char_location(self):
        if not self.token:
            return None

        current_location_name = None
        current_location_id = None

        r = httpx.get(
            ESI.ENDPOINT_ESI_LOCATION_FORMAT.format(self.char_id), headers=self._get_headers()
        )
        if r.status_code == httpx.codes.OK:
            current_location_id = r.json()["solar_system_id"]

        r = httpx.post(ESI.ENDPOINT_ESI_UNIVERSE_NAMES, json=[str(current_location_id)])
        if r.status_code == httpx.codes.OK:
            current_location_name = r.json()[0]["name"]

        return current_location_name

    def set_char_destination(self, sys_id):
        if not self.token:
            return False

        success = False
        r = httpx.post(
            "{}?add_to_beginning=false&clear_other_waypoints=true&destination_id={}".format(
                ESI.ENDPOINT_ESI_UI_WAYPOINT,
                sys_id,
            ),
            headers=self._get_headers(),
        )
        if r.status_code == 204:
            success = True

        return success

    def logout(self):
        self._logout()

    def _logout(self):
        with self._lock:
            char_id = self.char_id
            if self.sso_timer:
                self.sso_timer.cancel()
                self.sso_timer = None
            self.token = None
            self.refresh_token = None
            self.char_id = None
            self.char_name = None
        # Clear persisted credentials so restart doesn't silently log back in.
        # Safe to call unconditionally — both operations are no-ops if the
        # entries don't exist.
        if char_id is not None:
            ESI._delete_refresh_token(char_id)
        ESI._clear_persisted_char_id()
        self.logout_callback()


def login_cb(char_name):
    print("Welcome, {}".format(char_name))


def logout_cb():
    print("Session expired")


def main():
    import code

    implicit = True
    client_id = ""
    client_secret = ""

    esi = ESI(login_cb, logout_cb)
    print(esi.start_server())
    gvars = globals().copy()
    gvars.update(locals())
    shell = code.InteractiveConsole(gvars)
    shell.interact()


if __name__ == "__main__":
    main()
