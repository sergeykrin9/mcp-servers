"""
LinkedIn MCP server — publishes posts and reads profile via the official LinkedIn API.

Honest scope:
- LinkedIn's public API allows: posting on behalf of the authenticated user (w_member_social),
  reading the authenticated user's profile (r_liteprofile, r_emailaddress).
- It does NOT allow: searching connections, scraping other users' profiles, sending InMail,
  reading other people's posts. Those require Recruiter Lite / Sales Navigator / Marketing
  Developer Platform with formal app review.

So this MCP focuses on the realistic surface: publish your own posts, retrieve your own
profile, and use the resulting URN for analytics. For recruiter outreach and connection
management, the LinkedIn web UI remains the right tool.

Setup:
1. Create an app at https://www.linkedin.com/developers/apps
2. Add products: "Share on LinkedIn" (gives w_member_social) + "Sign In with LinkedIn"
3. Set redirect URL to http://localhost:8000/callback (or anything you control)
4. Get Client ID + Client Secret
5. Run oauth_helper.py once to obtain the access token (3-legged OAuth flow)
6. Drop the access token into .env as LINKEDIN_ACCESS_TOKEN

Then either drop into your .mcp.json or run standalone:
    python3 server.py
"""
from __future__ import annotations

import os
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("linkedin")

LINKEDIN_API = "https://api.linkedin.com/v2"
LINKEDIN_REST = "https://api.linkedin.com/rest"

ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
AUTHOR_URN_CACHE: str | None = None


def _headers() -> dict[str, str]:
    if not ACCESS_TOKEN:
        raise RuntimeError(
            "LINKEDIN_ACCESS_TOKEN env var is empty. Run oauth_helper.py first."
        )
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202405",
        "Content-Type": "application/json",
    }


def _author_urn() -> str:
    """Cache the authenticated user's URN — needed for posting."""
    global AUTHOR_URN_CACHE
    if AUTHOR_URN_CACHE:
        return AUTHOR_URN_CACHE
    r = requests.get(f"{LINKEDIN_API}/userinfo", headers=_headers(), timeout=15)
    r.raise_for_status()
    sub = r.json().get("sub")
    if not sub:
        raise RuntimeError(f"Could not resolve user URN from /userinfo: {r.json()}")
    AUTHOR_URN_CACHE = f"urn:li:person:{sub}"
    return AUTHOR_URN_CACHE


@mcp.tool()
def get_my_profile() -> dict[str, Any]:
    """Return the authenticated user's basic profile (id, name, email)."""
    r = requests.get(f"{LINKEDIN_API}/userinfo", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def publish_post(text: str, visibility: str = "PUBLIC") -> dict[str, Any]:
    """Publish a text post to the authenticated user's LinkedIn feed.

    Args:
        text: Post body. LinkedIn limit is 3000 characters.
        visibility: PUBLIC (default — visible to everyone) or CONNECTIONS (1st-degree only).

    Returns the new post's URN so the caller can link to it.
    """
    if len(text) > 3000:
        raise ValueError(f"Post too long: {len(text)} chars (LinkedIn limit is 3000)")
    if visibility not in {"PUBLIC", "CONNECTIONS"}:
        raise ValueError("visibility must be PUBLIC or CONNECTIONS")

    payload = {
        "author": _author_urn(),
        "commentary": text,
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    r = requests.post(
        f"{LINKEDIN_REST}/posts", headers=_headers(), json=payload, timeout=30
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Publish failed {r.status_code}: {r.text}")
    return {
        "ok": True,
        "post_urn": r.headers.get("x-restli-id"),
        "raw": r.json() if r.text else {},
    }


@mcp.tool()
def get_post_stats(post_urn: str) -> dict[str, Any]:
    """Get like/comment/share counts for one of YOUR posts.

    Args:
        post_urn: e.g. urn:li:ugcPost:1234567890 — returned by publish_post.
    """
    encoded = requests.utils.quote(post_urn, safe="")
    r = requests.get(
        f"{LINKEDIN_API}/socialActions/{encoded}", headers=_headers(), timeout=15
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def draft_post_from_repo(repo_url: str, hook_line: str) -> dict[str, Any]:
    """Draft a LinkedIn post promoting a GitHub repo. Does NOT publish — returns the text
    so the caller can review before calling publish_post.

    Args:
        repo_url: Full URL to the repo (e.g. https://github.com/user/repo).
        hook_line: The first 1-2 sentences that grab attention.
    """
    text = (
        f"{hook_line}\n\n"
        f"Just open-sourced it under MIT:\n"
        f"→ {repo_url}\n\n"
        "If this saves you time, drop a ⭐. Feedback welcome.\n\n"
        "#AI #ClaudeCode #LLM #OpenSource"
    )
    return {
        "ok": True,
        "draft": text,
        "char_count": len(text),
        "note": "Review then call publish_post(text=draft) to ship.",
    }


if __name__ == "__main__":
    mcp.run()
