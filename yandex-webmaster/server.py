#!/usr/bin/env python3
"""
Yandex Webmaster MCP server for edaru.su / yaeda.tb.ru / etc.
Uses OAuth token from tokens.json (auto-refreshed via oauth_helper.py).
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent
TOKEN_PATH = ROOT / "tokens.json"
ENV_PATH = ROOT / ".env"
API_BASE = "https://api.webmaster.yandex.net/v4"

load_dotenv(ENV_PATH)


def _access_token() -> str:
    if not TOKEN_PATH.exists():
        raise RuntimeError("tokens.json missing — run oauth_helper.py exchange first")
    payload = json.loads(TOKEN_PATH.read_text())
    tok = payload.get("access_token")
    if not tok:
        raise RuntimeError("No access_token in tokens.json")
    return tok


def _refresh_if_needed() -> None:
    """Refresh token if file says it expires soon (less than 7 days)."""
    if not TOKEN_PATH.exists():
        return
    try:
        from oauth_helper import do_refresh, load_config
        # We don't track wall-clock expiry locally; refresh opportunistically
        # only when API returns 401. For now, just load latest from disk.
    except Exception:
        pass


def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {"Authorization": f"OAuth {_access_token()}"}
    r = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=30)
    if r.status_code == 401:
        # try one auto-refresh then retry
        try:
            from oauth_helper import do_refresh, load_config
            cid, secret = load_config()
            do_refresh(cid, secret)
            headers = {"Authorization": f"OAuth {_access_token()}"}
            r = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=30)
        except Exception as e:
            return {"error": f"refresh failed: {e}", "status": 401}
    if r.status_code != 200:
        return {"error": r.text, "status": r.status_code}
    return r.json()


def _post(path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {"Authorization": f"OAuth {_access_token()}", "Content-Type": "application/json"}
    r = requests.post(f"{API_BASE}{path}", headers=headers, json=body or {}, timeout=30)
    if r.status_code == 401:
        try:
            from oauth_helper import do_refresh, load_config
            cid, secret = load_config()
            do_refresh(cid, secret)
            headers = {"Authorization": f"OAuth {_access_token()}", "Content-Type": "application/json"}
            r = requests.post(f"{API_BASE}{path}", headers=headers, json=body or {}, timeout=30)
        except Exception as e:
            return {"error": f"refresh failed: {e}", "status": 401}
    if r.status_code not in (200, 201, 202):
        return {"error": r.text, "status": r.status_code}
    # Some POSTs return empty body
    try:
        return r.json()
    except Exception:
        return {"ok": True, "status": r.status_code}


# Cached user_id (single-user app)
_USER_ID: Optional[int] = None


def _user_id() -> int:
    global _USER_ID
    if _USER_ID is None:
        data = _get("/user")
        _USER_ID = data.get("user_id")
        if not _USER_ID:
            raise RuntimeError(f"Cannot get user_id: {data}")
    return _USER_ID


def _normalize_host(host: str) -> str:
    """Convert 'edaru.su' / 'https://edaru.su' to Yandex host_id 'https:edaru.su:443'."""
    if ":" in host and host.count(":") >= 2 and ":443" in host:
        return host  # already in host_id form
    h = host.replace("https://", "").replace("http://", "").rstrip("/")
    return f"https:{h}:443"


mcp = FastMCP(
    "yandex-webmaster",
    instructions=(
        "Yandex.Webmaster API for site indexing, search queries, and external links. "
        "Use list_hosts() to see all sites, then get_summary/get_top_queries/get_indexed_pages "
        "for specifics. Pass host as 'edaru.su' (auto-normalized) or full host_id."
    ),
    json_response=True,
)


@mcp.tool()
def list_hosts() -> Dict[str, Any]:
    """Return all sites verified in Yandex.Webmaster for the current user."""
    data = _get(f"/user/{_user_id()}/hosts")
    if "error" in data:
        return data
    hosts = data.get("hosts", [])
    return {
        "count": len(hosts),
        "hosts": [
            {
                "host_id": h.get("host_id"),
                "verified": h.get("verified"),
                "ascii_host_url": h.get("ascii_host_url"),
            }
            for h in hosts
        ],
    }


@mcp.tool()
def get_summary(host: str) -> Dict[str, Any]:
    """Get site summary: pages in index, SQI score, problems, excluded pages count."""
    hid = _normalize_host(host)
    return _get(f"/user/{_user_id()}/hosts/{hid}/summary")


@mcp.tool()
def get_top_queries(
    host: str,
    days: int = 28,
    limit: int = 30,
    order_by: str = "TOTAL_SHOWS",
) -> Dict[str, Any]:
    """
    Top search queries by which the site is shown in Yandex search.
    Returns: query text, show position (avg), total shows, total clicks, CTR.
    order_by: TOTAL_SHOWS | TOTAL_CLICKS | AVG_SHOW_POSITION | AVG_CLICK_POSITION
    """
    hid = _normalize_host(host)
    date_to = date.today().isoformat()
    date_from = (date.today() - timedelta(days=days)).isoformat()
    return _get(
        f"/user/{_user_id()}/hosts/{hid}/search-queries/popular/",
        params={
            "query_indicator": [
                "TOTAL_SHOWS",
                "TOTAL_CLICKS",
                "AVG_SHOW_POSITION",
                "AVG_CLICK_POSITION",
            ],
            "order_by": order_by,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit,
        },
    )


@mcp.tool()
def get_indexed_pages(host: str, limit: int = 50) -> Dict[str, Any]:
    """Pages that Yandex has indexed (max ~100 per request)."""
    hid = _normalize_host(host)
    return _get(
        f"/user/{_user_id()}/hosts/{hid}/search-urls/in-search/samples/",
        params={"limit": limit},
    )


@mcp.tool()
def get_excluded_pages(host: str, limit: int = 30) -> Dict[str, Any]:
    """Pages that were excluded from index — shows reasons."""
    hid = _normalize_host(host)
    return _get(
        f"/user/{_user_id()}/hosts/{hid}/search-urls/excluded/samples/",
        params={"limit": limit},
    )


@mcp.tool()
def get_external_links_summary(host: str) -> Dict[str, Any]:
    """Summary of incoming external links (domains, link counts)."""
    hid = _normalize_host(host)
    return _get(f"/user/{_user_id()}/hosts/{hid}/links/external/main")


@mcp.tool()
def get_site_problems(host: str) -> Dict[str, Any]:
    """List of indexing/SEO problems detected by Yandex.Webmaster."""
    hid = _normalize_host(host)
    return _get(f"/user/{_user_id()}/hosts/{hid}/site-problems")


# ─────── Sitemap management ───────

@mcp.tool()
def list_sitemaps(host: str, limit: int = 100) -> Dict[str, Any]:
    """List all sitemaps (auto-discovered + user-added) registered for the host.
    Shows last_access, last_modified, items_count, errors_count."""
    hid = _normalize_host(host)
    return _get(f"/user/{_user_id()}/hosts/{hid}/sitemaps", params={"limit": limit})


@mcp.tool()
def add_sitemap(host: str, sitemap_url: str) -> Dict[str, Any]:
    """Register a new sitemap.xml (or sitemap-index) URL for the host. Up to 50 per host."""
    hid = _normalize_host(host)
    return _post(
        f"/user/{_user_id()}/hosts/{hid}/user-added-sitemaps",
        body={"url": sitemap_url},
    )


# ─────── Recrawl (force re-indexation) ───────

@mcp.tool()
def recrawl_url(host: str, url: str) -> Dict[str, Any]:
    """Submit a URL for forced re-crawl. Daily quota ~10 per host (depends on SQI).
    Returns task_id for status polling."""
    hid = _normalize_host(host)
    return _post(
        f"/user/{_user_id()}/hosts/{hid}/recrawl/queue",
        body={"url": url},
    )


@mcp.tool()
def get_recrawl_quota(host: str) -> Dict[str, Any]:
    """Get current recrawl quota status: daily_quota, quota_remainder."""
    hid = _normalize_host(host)
    return _get(f"/user/{_user_id()}/hosts/{hid}/recrawl/quota")


@mcp.tool()
def get_recrawl_status(host: str, task_id: str) -> Dict[str, Any]:
    """Check status of a specific recrawl task. Returns: state (PENDING/SCHEDULED/IN_PROGRESS/FAILED/DONE)."""
    hid = _normalize_host(host)
    return _get(f"/user/{_user_id()}/hosts/{hid}/recrawl/queue/{task_id}")


if __name__ == "__main__":
    mcp.run()
