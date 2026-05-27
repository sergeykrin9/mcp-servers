"""YouTube Data API v3 MCP server for edaru.su.

Provides read-only tools for competitor research, channel analysis, comment
harvest, and transcript extraction. Auth: API key (no OAuth — for upload
to @vdvige use a separate OAuth-based MCP).

Quota: default 10 000 units/day. Each search.list call costs 100 units.
"""
import os
from typing import Any, Dict, List, Optional

import requests
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ["YOUTUBE_API_KEY"]
BASE = "https://www.googleapis.com/youtube/v3"

mcp = FastMCP(
    "youtube",
    instructions=(
        "YouTube Data API v3 (read-only) for edaru.su SEO/arbitrage workflows. "
        "Use for: competitor research, @vdvige analytics input, comment harvesting, "
        "transcript extraction for content ideas, autocomplete keyword discovery. "
        "Auth: API key. For upload to @vdvige — separate OAuth MCP needed (pauling-ai)."
    ),
    json_response=True,
)


def _get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    p = {**params, "key": API_KEY}
    r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=30)
    r.raise_for_status()
    return r.json()


def _autocomplete(query: str, hl: str = "ru") -> List[str]:
    """YouTube autocomplete (uses internal endpoint, no API key, no quota)."""
    url = "https://suggestqueries-clients6.youtube.com/complete/search"
    params = {"client": "youtube", "ds": "yt", "q": query, "hl": hl}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    # response: window.google.ac.h(["query",[["suggestion",0],...]])
    text = r.text
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    import json
    try:
        data = json.loads(text[start : end + 1])
        return [item[0] for item in data[1] if isinstance(item, list)]
    except Exception:
        return []


@mcp.tool()
def search_videos(
    query: str,
    max_results: int = 25,
    region_code: str = "RU",
    relevance_language: str = "ru",
    order: str = "relevance",
    published_after: Optional[str] = None,
) -> Dict[str, Any]:
    """Search YouTube for videos. order: relevance|date|viewCount|rating|title.
    published_after: ISO 8601 like '2026-01-01T00:00:00Z'. Cost: 100 units."""
    params: Dict[str, Any] = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "regionCode": region_code,
        "relevanceLanguage": relevance_language,
        "order": order,
    }
    if published_after:
        params["publishedAfter"] = published_after
    data = _get("search", params)
    items = [
        {
            "videoId": i["id"]["videoId"],
            "title": i["snippet"]["title"],
            "channelTitle": i["snippet"]["channelTitle"],
            "channelId": i["snippet"]["channelId"],
            "publishedAt": i["snippet"]["publishedAt"],
            "description": i["snippet"]["description"][:200],
            "thumbnail": i["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        }
        for i in data.get("items", [])
    ]
    return {"query": query, "count": len(items), "items": items}


@mcp.tool()
def search_channels(query: str, max_results: int = 15, region_code: str = "RU") -> Dict[str, Any]:
    """Search YouTube for channels. Cost: 100 units."""
    data = _get(
        "search",
        {
            "part": "snippet",
            "q": query,
            "type": "channel",
            "maxResults": min(max_results, 50),
            "regionCode": region_code,
        },
    )
    items = [
        {
            "channelId": i["snippet"]["channelId"],
            "title": i["snippet"]["title"],
            "description": i["snippet"]["description"][:200],
            "thumbnail": i["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        }
        for i in data.get("items", [])
    ]
    return {"query": query, "count": len(items), "items": items}


@mcp.tool()
def get_channel(channel_id: Optional[str] = None, handle: Optional[str] = None) -> Dict[str, Any]:
    """Get channel info by id (UC...) OR by handle (@vdvige). Returns stats, snippet, branding."""
    params = {"part": "snippet,statistics,brandingSettings,contentDetails"}
    if channel_id:
        params["id"] = channel_id
    elif handle:
        params["forHandle"] = handle.lstrip("@")
    else:
        raise ValueError("Provide channel_id or handle")
    data = _get("channels", params)
    if not data.get("items"):
        return {"found": False}
    ch = data["items"][0]
    return {
        "found": True,
        "id": ch["id"],
        "title": ch["snippet"]["title"],
        "customUrl": ch["snippet"].get("customUrl", ""),
        "publishedAt": ch["snippet"]["publishedAt"],
        "description": ch["snippet"]["description"],
        "country": ch["snippet"].get("country", ""),
        "subscriberCount": ch["statistics"].get("subscriberCount", "0"),
        "videoCount": ch["statistics"].get("videoCount", "0"),
        "viewCount": ch["statistics"].get("viewCount", "0"),
        "uploadsPlaylistId": ch["contentDetails"]["relatedPlaylists"]["uploads"],
        "thumbnail": ch["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        "keywords": ch.get("brandingSettings", {}).get("channel", {}).get("keywords", ""),
    }


@mcp.tool()
def list_channel_videos(channel_id: str, max_results: int = 50) -> Dict[str, Any]:
    """List recent videos uploaded by a channel. Cost: 1 unit per call."""
    # Get uploads playlist
    ch_data = _get("channels", {"part": "contentDetails", "id": channel_id})
    if not ch_data.get("items"):
        return {"found": False}
    uploads_id = ch_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    # Fetch playlist items
    data = _get(
        "playlistItems",
        {
            "part": "snippet,contentDetails",
            "playlistId": uploads_id,
            "maxResults": min(max_results, 50),
        },
    )
    items = [
        {
            "videoId": i["contentDetails"]["videoId"],
            "title": i["snippet"]["title"],
            "publishedAt": i["contentDetails"].get("videoPublishedAt", i["snippet"]["publishedAt"]),
            "description": i["snippet"]["description"][:200],
        }
        for i in data.get("items", [])
    ]
    return {"channel_id": channel_id, "count": len(items), "items": items}


@mcp.tool()
def get_video(video_id: str) -> Dict[str, Any]:
    """Get full video metadata + statistics. Cost: 1 unit."""
    data = _get(
        "videos",
        {"part": "snippet,statistics,contentDetails,topicDetails", "id": video_id},
    )
    if not data.get("items"):
        return {"found": False}
    v = data["items"][0]
    return {
        "found": True,
        "id": v["id"],
        "title": v["snippet"]["title"],
        "channelTitle": v["snippet"]["channelTitle"],
        "channelId": v["snippet"]["channelId"],
        "publishedAt": v["snippet"]["publishedAt"],
        "description": v["snippet"]["description"],
        "tags": v["snippet"].get("tags", []),
        "categoryId": v["snippet"].get("categoryId", ""),
        "duration": v["contentDetails"]["duration"],
        "viewCount": v["statistics"].get("viewCount", "0"),
        "likeCount": v["statistics"].get("likeCount", "0"),
        "commentCount": v["statistics"].get("commentCount", "0"),
        "topicCategories": v.get("topicDetails", {}).get("topicCategories", []),
    }


@mcp.tool()
def get_video_comments(video_id: str, max_results: int = 50, order: str = "relevance") -> Dict[str, Any]:
    """Get top-level comments. order: time|relevance. Cost: 1 unit per call."""
    data = _get(
        "commentThreads",
        {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": order,
            "textFormat": "plainText",
        },
    )
    items = [
        {
            "author": c["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
            "text": c["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
            "likeCount": c["snippet"]["topLevelComment"]["snippet"]["likeCount"],
            "publishedAt": c["snippet"]["topLevelComment"]["snippet"]["publishedAt"],
            "totalReplies": c["snippet"]["totalReplyCount"],
        }
        for c in data.get("items", [])
    ]
    return {"video_id": video_id, "count": len(items), "items": items}


@mcp.tool()
def get_trending_videos(region_code: str = "RU", category_id: Optional[str] = None, max_results: int = 30) -> Dict[str, Any]:
    """Get currently trending videos in a region. Cost: 1 unit."""
    params: Dict[str, Any] = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),
    }
    if category_id:
        params["videoCategoryId"] = category_id
    data = _get("videos", params)
    items = [
        {
            "videoId": v["id"],
            "title": v["snippet"]["title"],
            "channelTitle": v["snippet"]["channelTitle"],
            "channelId": v["snippet"]["channelId"],
            "publishedAt": v["snippet"]["publishedAt"],
            "viewCount": v["statistics"].get("viewCount", "0"),
            "likeCount": v["statistics"].get("likeCount", "0"),
        }
        for v in data.get("items", [])
    ]
    return {"region": region_code, "count": len(items), "items": items}


@mcp.tool()
def autocomplete_suggestions(query: str, language: str = "ru") -> Dict[str, Any]:
    """YouTube autocomplete suggestions for a query — what users type after this seed.
    No API quota cost (uses public autocomplete endpoint). Use for SEO keyword discovery."""
    suggestions = _autocomplete(query, hl=language)
    return {"query": query, "language": language, "count": len(suggestions), "suggestions": suggestions}


@mcp.tool()
def get_video_transcript(video_id: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Get auto-generated or manual transcript/captions for a video.
    Uses youtube-transcript-api (no quota cost). language: 'ru', 'en', etc."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {"error": "youtube-transcript-api not installed in venv"}

    try:
        if language:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript([language])
            except Exception:
                transcript = transcript_list.find_generated_transcript([language])
            data = transcript.fetch()
        else:
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=["ru", "en"])
        # Trim long transcripts
        full_text = " ".join(s.get("text", "") for s in data)
        return {
            "video_id": video_id,
            "language": language or "ru/en",
            "segments": len(data),
            "duration_total": data[-1]["start"] + data[-1]["duration"] if data else 0,
            "text_preview": full_text[:2000] + ("..." if len(full_text) > 2000 else ""),
            "full_segments": data[:50],  # first 50 segments with timestamps
        }
    except Exception as e:
        return {"error": str(e), "video_id": video_id}


@mcp.tool()
def get_quota_estimate() -> Dict[str, Any]:
    """Documentation tool — return quota costs for each method (no API call)."""
    return {
        "daily_default_quota": 10000,
        "costs_per_call": {
            "search_videos": 100,
            "search_channels": 100,
            "get_channel": 1,
            "list_channel_videos": 2,  # 1 channels.list + 1 playlistItems.list
            "get_video": 1,
            "get_video_comments": 1,
            "get_trending_videos": 1,
            "autocomplete_suggestions": 0,
            "get_video_transcript": 0,
            "get_quota_estimate": 0,
        },
        "note": "10K/day = ~100 search calls OR ~10K cheap calls. Plan multi-step research carefully.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
