"""
LinkedIn OAuth helper. Run once to obtain a long-lived access token,
then drop the printed token into .env as LINKEDIN_ACCESS_TOKEN.

Usage:
    1. Create an app at https://www.linkedin.com/developers/apps
    2. Products: add "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect"
    3. Auth tab: set redirect URL to http://localhost:8765/callback
    4. Note Client ID + Client Secret — drop into .env
    5. Run: python3 oauth_helper.py
    6. Browser opens → log in → approve scopes → callback hits this script
    7. Script prints the access token. Copy to .env.

Required scopes: openid profile email w_member_social
- openid + profile + email — needed for /userinfo (gives us your URN)
- w_member_social — needed to post on your feed
"""
from __future__ import annotations

import http.server
import os
import secrets
import socketserver
import sys
import urllib.parse
import webbrowser

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8765/callback")
PORT = int(urllib.parse.urlparse(REDIRECT_URI).port or 8765)

SCOPES = ["openid", "profile", "email", "w_member_social"]
STATE = secrets.token_urlsafe(16)

if not CLIENT_ID or not CLIENT_SECRET:
    print(
        "ERROR: set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env first.\n"
        "Get them from https://www.linkedin.com/developers/apps → your app → Auth tab.",
        file=sys.stderr,
    )
    sys.exit(1)

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(
    {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": STATE,
        "scope": " ".join(SCOPES),
    }
)

received_code: str | None = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        return

    def do_GET(self):
        global received_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path != urllib.parse.urlparse(REDIRECT_URI).path:
            self.send_response(404)
            self.end_headers()
            return

        state = params.get("state", [None])[0]
        if state != STATE:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch — possible CSRF. Restart the script.")
            return

        received_code = params.get("code", [None])[0]
        if not received_code:
            err = params.get("error_description", ["unknown"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"OAuth error: {err}".encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<h1>Authorized</h1><p>Return to your terminal — the token is being printed.</p>"
        )


def exchange_for_token(code: str) -> dict:
    r = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def main():
    print(f"\n→ Opening browser for LinkedIn login...")
    print(f"   If it doesn't open, paste this URL manually:\n   {AUTH_URL}\n")
    webbrowser.open(AUTH_URL)

    with socketserver.TCPServer(("", PORT), CallbackHandler) as httpd:
        print(f"   Waiting for callback on port {PORT}...")
        while received_code is None:
            httpd.handle_request()

    print(f"\n→ Exchanging authorization code for access token...")
    tokens = exchange_for_token(received_code)

    print("\n✅ SUCCESS\n")
    print("Add this to your .env (or .mcp.json env block):\n")
    print(f"LINKEDIN_ACCESS_TOKEN={tokens['access_token']}")
    print(f"# Expires in {tokens.get('expires_in', '?')} seconds")
    if "refresh_token" in tokens:
        print(f"LINKEDIN_REFRESH_TOKEN={tokens['refresh_token']}")
    print()


if __name__ == "__main__":
    main()
