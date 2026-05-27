#!/usr/bin/env python3
"""
Yandex OAuth helper for Webmaster (+ Metrika + Direct combined).

Usage:
    python3 oauth_helper.py print-url       # генерит URL — открой в браузере, разреши, получишь code
    python3 oauth_helper.py exchange <CODE> # обменивает code на access+refresh токены
    python3 oauth_helper.py refresh         # обновляет токен через refresh_token
    python3 oauth_helper.py whoami          # показывает текущий токен и его scope
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
TOKEN_PATH = ROOT / "tokens.json"
OAUTH_BASE = "https://oauth.yandex.ru"
REDIRECT_URI = f"{OAUTH_BASE}/verification_code"

# Scopes: Webmaster (главное), плюс Metrika и Direct read для удобства
# (если этот же OAuth app выдаёт токен и для других сервисов).
# webmaster:hostinfo — чтение информации по сайтам
# webmaster:verify — добавление/верификация сайтов (на случай если понадобится)
SCOPES = "webmaster:hostinfo webmaster:verify webmaster:turbopages"


def load_config():
    load_dotenv(ENV_PATH)
    cid = os.getenv("YANDEX_WEBMASTER_CLIENT_ID")
    secret = os.getenv("YANDEX_WEBMASTER_CLIENT_SECRET")
    if not cid or not secret:
        raise SystemExit("Missing YANDEX_WEBMASTER_CLIENT_ID/SECRET in .env")
    return cid, secret


def build_authorize_url(cid):
    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "force_confirm": "yes",
        "device_name": "edaru.su Webmaster MCP",
    }
    return f"{OAUTH_BASE}/authorize?{urlencode(params)}"


def exchange_code(cid, secret, code):
    r = requests.post(
        f"{OAUTH_BASE}/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cid,
            "client_secret": secret,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    TOKEN_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def do_refresh(cid, secret):
    if not TOKEN_PATH.exists():
        raise SystemExit("No tokens.json yet — run `exchange <CODE>` first")
    payload = json.loads(TOKEN_PATH.read_text())
    rt = payload.get("refresh_token")
    if not rt:
        raise SystemExit("No refresh_token in tokens.json")
    r = requests.post(
        f"{OAUTH_BASE}/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": cid,
            "client_secret": secret,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    TOKEN_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def whoami():
    if not TOKEN_PATH.exists():
        return {"error": "no token saved yet"}
    payload = json.loads(TOKEN_PATH.read_text())
    return {
        "access_token_prefix": (payload.get("access_token") or "")[:18] + "...",
        "expires_in": payload.get("expires_in"),
        "token_type": payload.get("token_type"),
        "scope": payload.get("scope"),
        "has_refresh": bool(payload.get("refresh_token")),
    }


def main():
    cid, secret = load_config()

    if len(sys.argv) < 2:
        sys.exit(
            "Usage:\n"
            "  python3 oauth_helper.py print-url\n"
            "  python3 oauth_helper.py exchange <CODE>\n"
            "  python3 oauth_helper.py refresh\n"
            "  python3 oauth_helper.py whoami"
        )

    cmd = sys.argv[1]

    if cmd == "print-url":
        print(build_authorize_url(cid))
        return

    if cmd == "exchange":
        if len(sys.argv) < 3:
            sys.exit("Need <CODE> argument")
        data = exchange_code(cid, secret, sys.argv[2])
        print(json.dumps({"status": "saved", "scope": data.get("scope"), "expires_in": data.get("expires_in")}, ensure_ascii=False, indent=2))
        return

    if cmd == "refresh":
        data = do_refresh(cid, secret)
        print(json.dumps({"status": "refreshed", "expires_in": data.get("expires_in")}, ensure_ascii=False, indent=2))
        return

    if cmd == "whoami":
        print(json.dumps(whoami(), ensure_ascii=False, indent=2))
        return

    sys.exit(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
