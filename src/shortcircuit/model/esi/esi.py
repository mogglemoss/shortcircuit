# esi.py

import base64
import hashlib
import json
import secrets
import threading
import uuid
import webbrowser

import httpx
from shortcircuit.model.logger import Logger
from shortcircuit import USER_AGENT

from .server import AuthHandler, StoppableHTTPServer


class ESI:
    ENDPOINT_ESI_LOCATION_FORMAT = "https://esi.evetech.net/latest/characters/{}/location/"
    ENDPOINT_ESI_UNIVERSE_NAMES = "https://esi.evetech.net/latest/universe/names/"
    ENDPOINT_ESI_UI_WAYPOINT = "https://esi.evetech.net/latest/ui/autopilot/waypoint/"

    ENDPOINT_EVE_TOKEN = "https://login.eveonline.com/v2/oauth/token"
    ENDPOINT_EVE_AUTH_FORMAT = (
        "https://login.eveonline.com/v2/oauth/authorize"
        "?response_type=code&redirect_uri={}&client_id={}&scope={}&state={}"
        "&code_challenge={}&code_challenge_method=S256"
    )
    CLIENT_CALLBACK = "http://127.0.0.1:7444/callback/"
    CLIENT_ID = "d802bba44b7c4f6cbfa2944b0e5ea83f"
    CLIENT_SCOPES = [
        "esi-location.read_location.v1",
        "esi-ui.write_waypoint.v1",
    ]

    def __init__(self, login_callback, logout_callback):
        self.login_callback = login_callback
        self.logout_callback = logout_callback
        self.httpd = None
        self.state = None
        self.code_verifier = None

        self.token = None
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
        scopes = " ".join(ESI.CLIENT_SCOPES)
        endpoint_auth = ESI.ENDPOINT_EVE_AUTH_FORMAT.format(
            ESI.CLIENT_CALLBACK, ESI.CLIENT_ID, scopes, self.state, code_challenge
        )

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

        # Exchange auth code for access token (PKCE flow)
        r = httpx.post(
            ESI.ENDPOINT_EVE_TOKEN,
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
            self.token = token_data["access_token"]
            self.sso_timer = threading.Timer(int(token_data["expires_in"]), self._logout)
            self.sso_timer.daemon = True
            self.sso_timer.start()

            # Decode character info from the JWT access token. CCP removed the
            # /verify REST endpoint on 24 March 2026 in favour of offline JWT
            # decoding.
            try:
                claims = self._decode_jwt_payload(self.token)
                sub = claims.get("sub", "")
                # sub looks like "CHARACTER:EVE:12345"
                char_id = int(sub.rsplit(":", 1)[-1])
                char_name = str(claims.get("name", "Unknown"))
                self.char_id = char_id
                self.char_name = char_name
                self.login_callback(
                    {"is_ok": True, "char_name": self.char_name, "char_id": self.char_id}
                )
            except (ValueError, KeyError, IndexError) as e:
                Logger.warning("Failed to decode JWT claims: {}".format(e))
                self._reset_auth()
                self.login_callback({"is_ok": False, "char_name": None, "char_id": 0})
        else:
            Logger.warning("Token exchange failed: {} {}".format(r.status_code, r.text))
            self._reset_auth()
            self.login_callback({"is_ok": False, "char_name": None, "char_id": 0})

        self.stop_server()

    def _reset_auth(self):
        self.token = None
        self.sso_timer = None
        self.char_id = None
        self.char_name = None

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
        if self.sso_timer:
            self.sso_timer.cancel()
        self._logout()

    def _logout(self):
        self.token = None
        self.char_id = None
        self.char_name = None
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
