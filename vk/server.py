"""VK API MCP server for edaru.su community posting (vk.com/edaru).

Auth: community access token (созданный в Управление → Настройки → API).
Токен без срока, привязан к группе, не требует OAuth flow.

Scope нужен: wall, photos, manage.

Posting flow для фото:
  1. photos.getWallUploadServer → upload_url
  2. POST upload_url (multipart) → server, photo, hash
  3. photos.saveWallPhoto → owner_id, id
  4. wall.post с attachments=photo{owner_id}_{id}

Лимиты: 20 req/sec, ~50 постов/сутки на стену.
"""
import os
from typing import Any, Dict, List, Optional

import requests
from mcp.server.fastmcp import FastMCP

VK_TOKEN = os.environ.get("VK_TOKEN", "")
VK_GROUP_ID = os.environ.get("VK_GROUP_ID", "")  # number, без минуса
VK_API_VERSION = "5.199"
VK_BASE = "https://api.vk.com/method"

mcp = FastMCP(
    "vk",
    instructions=(
        "VK API server for edaru.su community (vk.com/edaru). "
        "Use post_to_wall to publish posts, attach_photo for image upload. "
        "Default group is configured via VK_GROUP_ID env. Brand voice: brand_voice_edaru.md."
    ),
    json_response=True,
)


def _check_token() -> None:
    if not VK_TOKEN:
        raise RuntimeError("VK_TOKEN env var not set — Сергей даёт community token via UI")


def _call(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _check_token()
    p = {"access_token": VK_TOKEN, "v": VK_API_VERSION, **(params or {})}
    r = requests.post(f"{VK_BASE}/{method}", data=p, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        return {"error": data["error"], "method": method}
    return data.get("response", data)


def _resolve_owner_id(group_id: Optional[str] = None) -> str:
    """Convert positive group_id (12345) to negative owner_id format (-12345) for wall ops."""
    gid = group_id or VK_GROUP_ID
    if not gid:
        raise ValueError("group_id is required when VK_GROUP_ID is not set")
    gid_str = str(gid).lstrip("-")
    return f"-{gid_str}"


@mcp.tool()
def get_me() -> Dict[str, Any]:
    """Verify token works. Returns user/group info attached to token."""
    return _call("users.get", {"fields": "screen_name,first_name"})


@mcp.tool()
def get_group_info(group_id: Optional[str] = None) -> Dict[str, Any]:
    """Get info about the configured (or specified) community."""
    gid = (group_id or VK_GROUP_ID).lstrip("-")
    return _call(
        "groups.getById",
        {"group_id": gid, "fields": "members_count,description,site,activity"},
    )


@mcp.tool()
def post_to_wall(
    message: str,
    group_id: Optional[str] = None,
    photo_url: Optional[str] = None,
    attachments: Optional[str] = None,
    publish_date_unix: Optional[int] = None,
    from_group: bool = True,
    signed: bool = False,
) -> Dict[str, Any]:
    """Publish a post to community wall.
    photo_url: download + upload via 4-step flow + attach automatically.
    attachments: pre-built attachments string like 'photo-12345_67890,link'.
    publish_date_unix: schedule (unix timestamp) — VK supports postpone up to 365 days.
    """
    owner_id = _resolve_owner_id(group_id)
    params: Dict[str, Any] = {
        "owner_id": owner_id,
        "message": message,
        "from_group": 1 if from_group else 0,
        "signed": 1 if signed else 0,
    }
    final_attachments: List[str] = []
    if attachments:
        final_attachments.append(attachments)
    if photo_url:
        photo_attachment = _upload_photo_from_url(photo_url, group_id)
        if "error" in photo_attachment:
            return photo_attachment
        final_attachments.append(photo_attachment["attachment"])
    if final_attachments:
        params["attachments"] = ",".join(final_attachments)
    if publish_date_unix:
        params["publish_date"] = publish_date_unix
    result = _call("wall.post", params)
    if "post_id" in result:
        result["url"] = f"https://vk.com/wall{owner_id}_{result['post_id']}"
    return result


def _upload_photo_from_url(photo_url: str, group_id: Optional[str] = None) -> Dict[str, Any]:
    """4-step photo upload to wall. Returns {'attachment': 'photo-X_Y'}."""
    gid = (group_id or VK_GROUP_ID).lstrip("-")
    # 1. Get upload server
    server_resp = _call("photos.getWallUploadServer", {"group_id": gid})
    if "error" in server_resp:
        return server_resp
    upload_url = server_resp["upload_url"]
    # 2. Download image, upload to VK server
    img_data = requests.get(photo_url, timeout=30).content
    files = {"photo": ("image.jpg", img_data, "image/jpeg")}
    up = requests.post(upload_url, files=files, timeout=30).json()
    if up.get("photo") in (None, "", "[]"):
        return {"error": "VK upload failed — image rejected", "raw": up}
    # 3. Save photo
    save_resp = _call(
        "photos.saveWallPhoto",
        {
            "group_id": gid,
            "server": up["server"],
            "photo": up["photo"],
            "hash": up["hash"],
        },
    )
    if "error" in save_resp:
        return save_resp
    photo = save_resp[0] if isinstance(save_resp, list) else save_resp
    # 4. Build attachment string
    return {"attachment": f"photo{photo['owner_id']}_{photo['id']}"}


@mcp.tool()
def upload_photo(photo_url: str, group_id: Optional[str] = None) -> Dict[str, Any]:
    """Upload a photo from public URL. Returns attachment string for use in post_to_wall."""
    return _upload_photo_from_url(photo_url, group_id)


@mcp.tool()
def edit_post(
    post_id: int,
    message: Optional[str] = None,
    attachments: Optional[str] = None,
    group_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Edit an existing wall post."""
    params: Dict[str, Any] = {
        "owner_id": _resolve_owner_id(group_id),
        "post_id": post_id,
    }
    if message is not None:
        params["message"] = message
    if attachments is not None:
        params["attachments"] = attachments
    return _call("wall.edit", params)


@mcp.tool()
def delete_post(post_id: int, group_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete a wall post by post_id."""
    return _call(
        "wall.delete",
        {"owner_id": _resolve_owner_id(group_id), "post_id": post_id},
    )


@mcp.tool()
def pin_post(post_id: int, group_id: Optional[str] = None) -> Dict[str, Any]:
    """Pin a post to the top of the wall."""
    return _call(
        "wall.pin",
        {"owner_id": _resolve_owner_id(group_id), "post_id": post_id},
    )


@mcp.tool()
def get_post_stats(post_id: int, group_id: Optional[str] = None) -> Dict[str, Any]:
    """Get reach + engagement stats for a post."""
    owner_id = _resolve_owner_id(group_id)
    reach = _call(
        "stats.getPostReach",
        {"owner_id": owner_id, "post_ids": str(post_id)},
    )
    by_id = _call(
        "wall.getById",
        {"posts": f"{owner_id}_{post_id}", "extended": 1},
    )
    return {"reach": reach, "post": by_id}


@mcp.tool()
def get_recent_posts(group_id: Optional[str] = None, count: int = 10) -> Dict[str, Any]:
    """Get recent posts from community wall — useful for dedup in daily-poster."""
    return _call(
        "wall.get",
        {"owner_id": _resolve_owner_id(group_id), "count": min(count, 100)},
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
