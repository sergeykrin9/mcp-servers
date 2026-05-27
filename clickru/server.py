#!/usr/bin/env python3
"""
Click.ru MCP Server — unified access to Yandex Direct, VK Ads, Telegram Ads,
MyTarget and other advertising platforms via Click.ru aggregator API.

API docs: https://api.click.ru/V0/docs/
Auth: X-Auth-Token header, optional X-Auth-UserId for master accounts.
Rate limits: 5 req/s, 3600 req/h.
"""

import os
import json
import httpx
from typing import Optional
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = "https://api.click.ru/V0"
API_TOKEN = os.environ.get("CLICKRU_API_KEY", "")
ACCOUNT_ID = os.environ.get("CLICKRU_ACCOUNT_ID", "")

mcp = FastMCP("clickru")

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _headers(user_id: Optional[str] = None) -> dict:
    """Build auth headers for Click.ru API."""
    h = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Auth-Token": API_TOKEN,
    }
    uid = user_id or ACCOUNT_ID
    if uid:
        h["X-Auth-UserId"] = uid
    return h


async def _get(path: str, params: Optional[dict] = None, user_id: Optional[str] = None) -> dict:
    """Perform GET request to Click.ru API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{API_BASE}{path}",
            headers=_headers(user_id),
            params=params,
        )
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: Optional[dict] = None, user_id: Optional[str] = None) -> dict:
    """Perform POST request to Click.ru API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{API_BASE}{path}",
            headers=_headers(user_id),
            json=body or {},
        )
        r.raise_for_status()
        return r.json()


async def _put(path: str, body: Optional[dict] = None, user_id: Optional[str] = None) -> dict:
    """Perform PUT request to Click.ru API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.put(
            f"{API_BASE}{path}",
            headers=_headers(user_id),
            json=body or {},
        )
        r.raise_for_status()
        return r.json()


async def _delete(path: str, user_id: Optional[str] = None) -> dict:
    """Perform DELETE request to Click.ru API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.delete(
            f"{API_BASE}{path}",
            headers=_headers(user_id),
        )
        r.raise_for_status()
        return r.json()


def _fmt(data) -> str:
    """Pretty-format JSON response."""
    return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Tools — User & Account management
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_user() -> str:
    """Get current Click.ru user profile (name, email, balance, role)."""
    try:
        data = await _get("/user")
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_accounts(user_id: Optional[str] = None) -> str:
    """List all advertising accounts connected to Click.ru.
    Returns accounts across all platforms (Yandex Direct, VK Ads, Telegram Ads, etc.).
    Optionally specify user_id to query on behalf of a sub-user (master accounts).
    """
    try:
        data = await _get("/accounts", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_balance(user_id: Optional[str] = None) -> str:
    """Get current Click.ru account balance and financial summary."""
    try:
        data = await _get("/user/balance", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        # Try alternative endpoint
        try:
            data = await _get("/user", user_id=user_id)
            return _fmt(data)
        except Exception:
            return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Campaigns
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_campaigns(
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """List campaigns across all connected advertising platforms.
    Optionally filter by account_id. Returns campaign name, status, platform, budget.
    """
    aid = account_id or ACCOUNT_ID
    try:
        data = await _get(f"/accounts/{aid}/campaigns", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_campaign_stats(
    date_from: str,
    date_to: str,
    account_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    group_by: str = "day",
    user_id: Optional[str] = None,
) -> str:
    """Get campaign statistics for a date range.

    Args:
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        account_id: Filter by account (defaults to CLICKRU_ACCOUNT_ID).
        campaign_id: Filter by specific campaign.
        group_by: Grouping — 'day', 'campaign', 'account', 'platform'.
        user_id: Sub-user ID (for master accounts).
    """
    aid = account_id or ACCOUNT_ID
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "groupBy": group_by,
    }
    if campaign_id:
        params["campaignId"] = campaign_id
    try:
        data = await _get(f"/accounts/{aid}/stat", params=params, user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        # Try global stat endpoint
        try:
            data = await _get("/stat", params=params, user_id=user_id)
            return _fmt(data)
        except Exception:
            return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Statistics & Reports
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_reports(
    date_from: str,
    date_to: str,
    group_by: str = "day",
    metrics: str = "impressions,clicks,cost,ctr,cpc",
    user_id: Optional[str] = None,
) -> str:
    """Pull analytics reports across all advertising platforms.

    Args:
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        group_by: Grouping — 'day', 'campaign', 'account', 'platform'.
        metrics: Comma-separated metrics: impressions, clicks, cost, ctr, cpc, conversions.
        user_id: Sub-user ID (for master accounts).
    """
    body = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "groupBy": group_by,
        "metrics": [m.strip() for m in metrics.split(",")],
    }
    try:
        data = await _post("/stat", body=body, user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        # Fallback: try GET with params
        try:
            params = {
                "dateFrom": date_from,
                "dateTo": date_to,
                "groupBy": group_by,
            }
            data = await _get("/stat", params=params, user_id=user_id)
            return _fmt(data)
        except Exception:
            return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Telegram Ads
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_telegram_channels(
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Browse available Telegram channels for advertising via Click.ru.
    Returns list of channels with audience stats, pricing, and categories.
    """
    aid = account_id or ACCOUNT_ID
    try:
        data = await _get(f"/telegram/{aid}/channels", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        # Try alternative endpoints
        try:
            data = await _get("/telegram/channels", user_id=user_id)
            return _fmt(data)
        except Exception:
            return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_telegram_ads(
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """List existing Telegram ad campaigns in Click.ru account."""
    aid = account_id or ACCOUNT_ID
    try:
        data = await _get(f"/telegram/{aid}/ads", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def create_telegram_ad(
    text: str,
    url: str,
    budget_total: float,
    budget_daily: Optional[float] = None,
    cpm: Optional[float] = None,
    channels: Optional[str] = None,
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Create a Telegram Ads campaign via Click.ru.

    Args:
        text: Ad text (up to 160 chars for Telegram Ads).
        url: Destination URL or Telegram channel link.
        budget_total: Total campaign budget in RUB.
        budget_daily: Daily budget limit in RUB.
        cpm: Cost per mille (1000 impressions) bid in RUB.
        channels: Comma-separated target channel IDs (optional).
        account_id: Advertising account ID.
        user_id: Sub-user ID (for master accounts).
    """
    aid = account_id or ACCOUNT_ID
    body = {
        "text": text,
        "url": url,
        "budgetTotal": budget_total,
    }
    if budget_daily is not None:
        body["budgetDaily"] = budget_daily
    if cpm is not None:
        body["cpm"] = cpm
    if channels:
        body["channels"] = [c.strip() for c in channels.split(",")]

    try:
        data = await _post(f"/telegram/{aid}/ads", body=body, user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Bid Manager
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_bid_manager(
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Get bid manager settings and status for an account.
    Shows auto-bidding configuration for Yandex Direct / Google Ads campaigns.
    """
    aid = account_id or ACCOUNT_ID
    try:
        data = await _get(f"/accounts/{aid}/bidmanager", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def toggle_bid_manager(
    enabled: bool,
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Enable or disable the bid manager for an account.

    Args:
        enabled: True to enable, False to disable auto-bidding.
        account_id: Advertising account ID.
        user_id: Sub-user ID.
    """
    aid = account_id or ACCOUNT_ID
    try:
        data = await _put(
            f"/accounts/{aid}/bidmanager",
            body={"enabled": enabled},
            user_id=user_id,
        )
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Keywords / Wordstat
# ---------------------------------------------------------------------------

@mcp.tool()
async def wordstat(
    keywords: str,
    region_ids: Optional[str] = None,
) -> str:
    """Get Yandex Wordstat data for keywords via Click.ru.
    Free alternative to direct Yandex API — no Yandex Direct account needed.

    Args:
        keywords: Comma-separated keywords to check search volume.
        region_ids: Comma-separated Yandex region IDs (e.g., '1' for Moscow).
    """
    body = {
        "keywords": [k.strip() for k in keywords.split(",")],
    }
    if region_ids:
        body["regionIds"] = [int(r.strip()) for r in region_ids.split(",")]

    try:
        data = await _post("/tools/beta/wordstat", body=body)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def wordstat_batch(
    keywords: str,
    region_ids: Optional[str] = None,
) -> str:
    """Batch Yandex Wordstat query — check search volume for many keywords at once.

    Args:
        keywords: Comma-separated keywords (up to 500).
        region_ids: Comma-separated Yandex region IDs.
    """
    body = {
        "keywords": [k.strip() for k in keywords.split(",")],
    }
    if region_ids:
        body["regionIds"] = [int(r.strip()) for r in region_ids.split(",")]

    try:
        data = await _post("/tools/beta/wordstat_batch", body=body)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Platform-specific access tokens
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_vk_ads_token(
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Get VK Ads API access token for direct VK Ads API calls.
    Useful for advanced VK Ads operations not covered by Click.ru API.
    """
    aid = account_id or ACCOUNT_ID
    try:
        data = await _get(f"/accounts/{aid}/access_token/vk_ads", user_id=user_id)
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Tools — Generic API call
# ---------------------------------------------------------------------------

@mcp.tool()
async def clickru_api_call(
    method: str,
    path: str,
    body: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Make an arbitrary Click.ru API call.
    Use this for endpoints not covered by other tools.
    Full API docs: https://api.click.ru/V0/docs/

    Args:
        method: HTTP method — GET, POST, PUT, DELETE.
        path: API path starting with / (e.g., '/user', '/accounts/123/campaigns').
        body: JSON body as string (for POST/PUT).
        user_id: Sub-user ID (for master accounts).
    """
    try:
        parsed_body = json.loads(body) if body else None
    except json.JSONDecodeError:
        return "Error: invalid JSON in body parameter"

    try:
        m = method.upper()
        if m == "GET":
            data = await _get(path, user_id=user_id)
        elif m == "POST":
            data = await _post(path, body=parsed_body, user_id=user_id)
        elif m == "PUT":
            data = await _put(path, body=parsed_body, user_id=user_id)
        elif m == "DELETE":
            data = await _delete(path, user_id=user_id)
        else:
            return f"Error: unsupported method {method}"
        return _fmt(data)
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
