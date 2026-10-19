#!/usr/bin/env python3
"""
Google Search Console MCP server.
Uses existing axonleads-app Service Account JSON key.
"""
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

KEY_PATH = os.getenv("GSC_SERVICE_ACCOUNT_KEY", "")
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _service():
    if not KEY_PATH:
        raise RuntimeError("Set GSC_SERVICE_ACCOUNT_KEY to your service account JSON path")
    creds = service_account.Credentials.from_service_account_file(
        KEY_PATH, scopes=SCOPES
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _normalize_site(site: str) -> str:
    """Accept 'example.com' or 'https://example.com/' — normalize to GSC siteUrl format."""
    if site.startswith("http"):
        if not site.endswith("/"):
            site += "/"
        return site
    return f"https://{site}/"


mcp = FastMCP(
    "gsc",
    instructions=(
        "Google Search Console API. Use list_sites() to see all sites. "
        "Then get_top_queries / get_top_pages / query_position for specifics. "
        "Pass site as 'example.com' (auto-normalized to https://example.com/) or full siteUrl."
    ),
    json_response=True,
)


@mcp.tool()
def list_sites() -> Dict[str, Any]:
    """List all sites with permission for the GSC Service Account."""
    svc = _service()
    sites = svc.sites().list().execute()
    return {
        "count": len(sites.get("siteEntry", [])),
        "sites": [
            {"site_url": s.get("siteUrl"), "permission": s.get("permissionLevel")}
            for s in sites.get("siteEntry", [])
        ],
    }


@mcp.tool()
def get_top_queries(
    site: str,
    days: int = 28,
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Top search queries (clicks/impressions/CTR/position) for a site.
    Default last 28 days.
    """
    svc = _service()
    site_url = _normalize_site(site)
    body = {
        "startDate": (date.today() - timedelta(days=days)).isoformat(),
        "endDate": date.today().isoformat(),
        "dimensions": ["query"],
        "rowLimit": limit,
    }
    r = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    rows = r.get("rows", [])
    return {
        "site": site_url,
        "days": days,
        "count": len(rows),
        "queries": [
            {
                "query": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            }
            for row in rows
        ],
    }


@mcp.tool()
def get_top_pages(
    site: str,
    days: int = 28,
    limit: int = 30,
) -> Dict[str, Any]:
    """Top landing pages by clicks from Google search."""
    svc = _service()
    site_url = _normalize_site(site)
    body = {
        "startDate": (date.today() - timedelta(days=days)).isoformat(),
        "endDate": date.today().isoformat(),
        "dimensions": ["page"],
        "rowLimit": limit,
    }
    r = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    rows = r.get("rows", [])
    return {
        "site": site_url,
        "days": days,
        "count": len(rows),
        "pages": [
            {
                "url": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            }
            for row in rows
        ],
    }


@mcp.tool()
def query_position(
    site: str,
    query: str,
    days: int = 28,
) -> Dict[str, Any]:
    """Get position/impressions/clicks for a specific search query on a site."""
    svc = _service()
    site_url = _normalize_site(site)
    body = {
        "startDate": (date.today() - timedelta(days=days)).isoformat(),
        "endDate": date.today().isoformat(),
        "dimensions": ["query"],
        "dimensionFilterGroups": [
            {
                "filters": [
                    {"dimension": "query", "operator": "equals", "expression": query}
                ]
            }
        ],
        "rowLimit": 10,
    }
    r = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    rows = r.get("rows", [])
    if not rows:
        return {"site": site_url, "query": query, "found": False}
    row = rows[0]
    return {
        "site": site_url,
        "query": query,
        "found": True,
        "clicks": row.get("clicks", 0),
        "impressions": row.get("impressions", 0),
        "ctr": round(row.get("ctr", 0) * 100, 2),
        "position": round(row.get("position", 0), 1),
    }


@mcp.tool()
def get_country_breakdown(site: str, days: int = 28, limit: int = 20) -> Dict[str, Any]:
    """Breakdown of clicks/impressions by country (ISO codes)."""
    svc = _service()
    site_url = _normalize_site(site)
    body = {
        "startDate": (date.today() - timedelta(days=days)).isoformat(),
        "endDate": date.today().isoformat(),
        "dimensions": ["country"],
        "rowLimit": limit,
    }
    r = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    rows = r.get("rows", [])
    return {
        "site": site_url,
        "rows": [
            {
                "country": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
            }
            for row in rows
        ],
    }


@mcp.tool()
def get_indexed_status(site: str, url: str) -> Dict[str, Any]:
    """Check Google indexing status for a specific URL."""
    svc = _service()
    site_url = _normalize_site(site)
    try:
        r = (
            svc.urlInspection()
            .index()
            .inspect(body={"inspectionUrl": url, "siteUrl": site_url})
            .execute()
        )
        return r
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
