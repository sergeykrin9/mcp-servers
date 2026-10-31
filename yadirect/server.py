#!/usr/bin/env python3
"""
MCP Server for Yandex Direct API v5.

Provides tools for managing campaigns, ads, keywords, and reports
through the Yandex Direct advertising platform.

ENV: YANDEX_DIRECT_TOKEN — OAuth token for Yandex Direct API.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Any

import httpx

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("yadirect")

BASE_URL = "https://api.direct.yandex.com/json/v5"
REPORTS_URL = "https://api.direct.yandex.com/json/v5/reports"


def _get_token() -> str:
    token = os.environ.get("YANDEX_DIRECT_TOKEN", "")
    if not token:
        raise RuntimeError("YANDEX_DIRECT_TOKEN environment variable is not set")
    return token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept-Language": "ru",
        "Content-Type": "application/json; charset=utf-8",
    }


def _report_headers(return_money_in_micros: bool = False) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {_get_token()}",
        "Accept-Language": "ru",
        "Content-Type": "application/json; charset=utf-8",
        "processingMode": "auto",
        "returnMoneyInMicros": "true" if return_money_in_micros else "false",
        "skipReportHeader": "true",
        "skipReportSummary": "true",
        "skipColumnHeader": "false",
    }
    return h


def _call_api(service: str, method: str, params: dict[str, Any]) -> dict:
    """Make a call to Yandex Direct API v5."""
    url = f"{BASE_URL}/{service}"
    body = {"method": method, "params": params}
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=_headers(), json=body)
        resp.raise_for_status()
        data = resp.json()
    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"Yandex Direct API error {err.get('error_code')}: "
            f"{err.get('error_string')} — {err.get('error_detail')}"
        )
    return data


def _request_report(report_definition: dict, return_money_in_micros: bool = False) -> str:
    """
    Request a report from Yandex Direct Reports service.
    Polls queued (201) and pending (202) reports until ready (200).
    Returns the TSV report body as a string.
    """
    body = {"params": report_definition}
    headers = _report_headers(return_money_in_micros)

    with httpx.Client(timeout=120) as client:
        for attempt in range(30):
            resp = client.post(REPORTS_URL, headers=headers, json=body)

            if resp.status_code == 200:
                # Validate the column header, including header-only empty reports.
                actual_fields = resp.text.splitlines()[0].split("\t") if resp.text else []
                expected_fields = report_definition.get("FieldNames", [])
                if expected_fields and (len(actual_fields) != len(expected_fields) or
                                        set(actual_fields) != set(expected_fields)):
                    raise RuntimeError("Report response has an unexpected TSV header")
                return resp.text
            elif resp.status_code in (201, 202):
                # 201 means queued, not ready; 202 means still being generated.
                if attempt == 29:
                    break
                try:
                    retry_in = max(0, int(resp.headers.get("retryIn", 5)))
                except (TypeError, ValueError):
                    retry_in = 5
                time.sleep(retry_in)
                continue
            else:
                raise RuntimeError(
                    f"Report request failed with status {resp.status_code}: {resp.text}"
                )

    raise RuntimeError("Report generation timed out after 30 retries")


def _parse_tsv(tsv_text: str) -> list[dict[str, str]]:
    """Parse TSV report text into a list of dicts."""
    lines = [line for line in tsv_text.strip().split("\n") if line]
    if not lines:
        return []
    headers_row = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        rows.append(dict(zip(headers_row, values)))
    return rows


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_campaigns() -> str:
    """
    List all campaigns with Id, Name, State, Status, and DailyBudget.
    Returns JSON array of campaign objects.
    """
    result = _call_api(
        "campaigns",
        "get",
        {
            "SelectionCriteria": {},
            "FieldNames": ["Id", "Name", "State", "Status", "DailyBudget"],
        },
    )
    campaigns = result.get("result", {}).get("Campaigns", [])
    return json.dumps(campaigns, ensure_ascii=False, indent=2)


@mcp.tool()
def get_campaign_stats(campaign_id: int, days: int = 7) -> str:
    """
    Get campaign statistics for the last N days.
    Returns Impressions, Clicks, Cost, Conversions, CPA per day.
    Monetary values are in the account currency, including VAT, not micros.

    Args:
        campaign_id: The campaign ID to get stats for.
        days: Number of days to look back (default 7).
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")

    report_def = {
        "SelectionCriteria": {
            "Filter": [
                {"Field": "CampaignId", "Operator": "EQUALS", "Values": [str(campaign_id)]}
            ],
            "DateFrom": date_from,
            "DateTo": date_to,
        },
        "FieldNames": ["Date", "CampaignId", "Impressions", "Clicks", "Cost", "Conversions", "CostPerConversion"],
        "ReportName": f"campaign_{campaign_id}_stats_{date_from}_{date_to}",
        "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "YES",
    }

    tsv = _request_report(report_def, return_money_in_micros=False)
    rows = _parse_tsv(tsv)
    return json.dumps(rows, ensure_ascii=False, indent=2)


@mcp.tool()
def create_campaign(
    name: str,
    start_date: str,
    daily_budget_micros: int,
    negative_keywords: list[str] | None = None,
    goal_id: int = 0,
    weekly_spend_limit_micros: int = 0,
) -> str:
    """
    Create a new text campaign with MaximumConversions strategy (pay for conversions).

    Args:
        name: Campaign name.
        start_date: Start date in YYYY-MM-DD format.
        daily_budget_micros: Daily budget in micros (1 ruble = 1_000_000 micros).
        negative_keywords: List of negative keywords for the campaign.
        goal_id: Metrika goal ID for conversion optimization.
        weekly_spend_limit_micros: Weekly spend limit in micros for the strategy.
    """
    # MAX_PROFIT strategy (Максимум прибыли) — RSY only
    strategy = {
        "Search": {
            "BiddingStrategyType": "SERVING_OFF",
        },
        "Network": {
            "BiddingStrategyType": "AVERAGE_ROI",
            "AverageRoi": {
                "ReserveReturn": 50,
                "RoiCoefficient": 100000000,
            },
        },
    }

    if goal_id:
        strategy["Network"]["AverageRoi"]["GoalId"] = goal_id
    if weekly_spend_limit_micros:
        strategy["Network"]["AverageRoi"]["WeeklySpendLimit"] = weekly_spend_limit_micros

    campaign = {
        "Name": name,
        "StartDate": start_date,
        "DailyBudget": {
            "Amount": daily_budget_micros,
            "Mode": "STANDARD",
        },
        "NegativeKeywords": {"Items": negative_keywords or []},
        "TextCampaign": {
            "BiddingStrategy": strategy,
        },
    }

    result = _call_api("campaigns", "add", {"Campaigns": [campaign]})
    add_results = result.get("result", {}).get("AddResults", [])
    return json.dumps(add_results, ensure_ascii=False, indent=2)


@mcp.tool()
def update_campaign_bids(campaign_id: int, daily_budget_micros: int) -> str:
    """
    Update the daily budget for a campaign.

    Args:
        campaign_id: Campaign ID.
        daily_budget_micros: New daily budget in micros.
    """
    result = _call_api(
        "campaigns",
        "update",
        {
            "Campaigns": [
                {
                    "Id": campaign_id,
                    "DailyBudget": {
                        "Amount": daily_budget_micros,
                        "Mode": "STANDARD",
                    },
                }
            ]
        },
    )
    update_results = result.get("result", {}).get("UpdateResults", [])
    return json.dumps(update_results, ensure_ascii=False, indent=2)


@mcp.tool()
def pause_campaign(campaign_id: int) -> str:
    """
    Pause (suspend) a campaign.

    Args:
        campaign_id: Campaign ID to pause.
    """
    result = _call_api(
        "campaigns",
        "suspend",
        {"SelectionCriteria": {"Ids": [campaign_id]}},
    )
    return json.dumps({"status": "ok", "action": "suspended", "campaign_id": campaign_id})


@mcp.tool()
def resume_campaign(campaign_id: int) -> str:
    """
    Resume a paused campaign.

    Args:
        campaign_id: Campaign ID to resume.
    """
    result = _call_api(
        "campaigns",
        "resume",
        {"SelectionCriteria": {"Ids": [campaign_id]}},
    )
    return json.dumps({"status": "ok", "action": "resumed", "campaign_id": campaign_id})


@mcp.tool()
def get_ads(campaign_id: int) -> str:
    """
    List all ads in a campaign with their details.

    Args:
        campaign_id: Campaign ID.
    """
    result = _call_api(
        "ads",
        "get",
        {
            "SelectionCriteria": {"CampaignIds": [campaign_id]},
            "FieldNames": ["Id", "CampaignId", "AdGroupId", "State", "Status", "Type"],
            "TextAdFieldNames": ["Title", "Title2", "Text", "Href", "DisplayDomain", "Mobile"],
        },
    )
    ads = result.get("result", {}).get("Ads", [])
    return json.dumps(ads, ensure_ascii=False, indent=2)


@mcp.tool()
def update_ad_href(ad_id: int, new_href: str) -> str:
    """
    Update the link (Href) of an existing text ad.
    The ad will be re-sent for moderation after the update.

    Args:
        ad_id: The ad ID to update.
        new_href: The new URL (with UTM parameters).
    """
    result = _call_api(
        "ads",
        "update",
        {
            "Ads": [
                {
                    "Id": ad_id,
                    "TextAd": {"Href": new_href},
                }
            ]
        },
    )
    update_results = result.get("result", {}).get("UpdateResults", [])
    return json.dumps(update_results, ensure_ascii=False, indent=2)


@mcp.tool()
def get_keywords(ad_group_id: int) -> str:
    """
    List all keywords in an ad group.

    Args:
        ad_group_id: Ad group ID.
    """
    result = _call_api(
        "keywords",
        "get",
        {
            "SelectionCriteria": {"AdGroupIds": [ad_group_id]},
            "FieldNames": ["Id", "Keyword", "AdGroupId", "Bid", "ContextBid", "State", "Status"],
        },
    )
    keywords = result.get("result", {}).get("Keywords", [])
    return json.dumps(keywords, ensure_ascii=False, indent=2)


@mcp.tool()
def add_negative_keywords(campaign_id: int, negative_keywords: list[str]) -> str:
    """
    Add negative keywords to a campaign.

    Args:
        campaign_id: Campaign ID.
        negative_keywords: List of negative keyword strings to add.
    """
    # First get existing negative keywords
    get_result = _call_api(
        "campaigns",
        "get",
        {
            "SelectionCriteria": {"Ids": [campaign_id]},
            "FieldNames": ["Id", "NegativeKeywords"],
        },
    )
    campaigns = get_result.get("result", {}).get("Campaigns", [])
    if not campaigns:
        return json.dumps({"error": f"Campaign {campaign_id} not found"})

    existing = campaigns[0].get("NegativeKeywords", {}).get("Items", [])
    merged = list(set(existing + negative_keywords))

    result = _call_api(
        "campaigns",
        "update",
        {
            "Campaigns": [
                {
                    "Id": campaign_id,
                    "NegativeKeywords": {"Items": merged},
                }
            ]
        },
    )
    update_results = result.get("result", {}).get("UpdateResults", [])
    return json.dumps(
        {
            "campaign_id": campaign_id,
            "added": negative_keywords,
            "total_negatives": len(merged),
            "update_results": update_results,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def get_search_queries(campaign_id: int, days: int = 7) -> str:
    """
    Get search query performance report for a campaign.
    Shows actual search queries that triggered ads, with clicks, cost, and conversions.
    Monetary values are in the account currency, including VAT, not micros.

    Args:
        campaign_id: Campaign ID.
        days: Number of days to look back (default 7).
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")

    report_def = {
        "SelectionCriteria": {
            "Filter": [
                {"Field": "CampaignId", "Operator": "EQUALS", "Values": [str(campaign_id)]}
            ],
            "DateFrom": date_from,
            "DateTo": date_to,
        },
        "FieldNames": [
            "Query",
            "CampaignId",
            "Impressions",
            "Clicks",
            "Cost",
            "Conversions",
            "CostPerConversion",
        ],
        "ReportName": f"search_queries_{campaign_id}_{date_from}_{date_to}",
        "ReportType": "SEARCH_QUERY_PERFORMANCE_REPORT",
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "YES",
    }

    tsv = _request_report(report_def, return_money_in_micros=False)
    rows = _parse_tsv(tsv)

    # Sort by clicks descending for convenience
    rows.sort(key=lambda r: int(r.get("Clicks", "0")), reverse=True)

    return json.dumps(rows, ensure_ascii=False, indent=2)


@mcp.tool()
def get_daily_report(campaign_id: int, days: int = 30) -> str:
    """
    Get detailed daily statistics report for a campaign.
    Includes impressions, clicks, CTR, cost, avg CPC, conversions, and CPA per day.
    Monetary values are in the account currency, including VAT, not micros.

    Args:
        campaign_id: Campaign ID.
        days: Number of days to look back (default 30).
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")

    report_def = {
        "SelectionCriteria": {
            "Filter": [
                {"Field": "CampaignId", "Operator": "EQUALS", "Values": [str(campaign_id)]}
            ],
            "DateFrom": date_from,
            "DateTo": date_to,
        },
        "FieldNames": [
            "Date",
            "CampaignId",
            "CampaignName",
            "Impressions",
            "Clicks",
            "Ctr",
            "Cost",
            "AvgCpc",
            "Conversions",
            "CostPerConversion",
            "ConversionRate",
        ],
        "ReportName": f"daily_report_{campaign_id}_{date_from}_{date_to}",
        "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "YES",
    }

    tsv = _request_report(report_def, return_money_in_micros=False)
    rows = _parse_tsv(tsv)
    return json.dumps(rows, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
