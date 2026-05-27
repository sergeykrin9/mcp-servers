import os
from typing import Any, Dict, Optional

import requests
from mcp.server.fastmcp import FastMCP

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DEFAULT_CHAT_ID = os.environ.get("TELEGRAM_DEFAULT_CHAT_ID", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

mcp = FastMCP(
    "edaru-telegram",
    instructions=(
        "Telegram publishing server for edaru.su (@abg_taxi_group via @rabota2025vdostavkabot). "
        "Use it to publish, edit, delete, and pin posts in the configured channel. "
        "Default chat_id is @abg_taxi_group (-1001837403197). Brand voice rules in memory `brand_voice_edaru.md`."
    ),
    json_response=True,
)


def _post(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(f"{BASE_URL}/{method}", json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error for {method}: {data}")
    return data["result"]


def _get(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.get(f"{BASE_URL}/{method}", params=params or {}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error for {method}: {data}")
    return data["result"]


def _chat_id(chat_id: Optional[str]) -> str:
    resolved = chat_id or DEFAULT_CHAT_ID
    if not resolved:
        raise ValueError("chat_id is required when TELEGRAM_DEFAULT_CHAT_ID is not set")
    return resolved


@mcp.tool()
def get_me() -> Dict[str, Any]:
    """Return bot information for the current Telegram token."""
    return _get("getMe")


@mcp.tool()
def get_chat(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Return metadata for a Telegram chat or channel."""
    return _get("getChat", {"chat_id": _chat_id(chat_id)})


@mcp.tool()
def get_chat_administrators(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the admin list for a Telegram chat or channel."""
    admins = _get("getChatAdministrators", {"chat_id": _chat_id(chat_id)})
    return {"chat_id": _chat_id(chat_id), "administrators": admins}


@mcp.tool()
def publish_post(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
    disable_notification: bool = False,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Publish a text post to the default channel or a provided chat_id. reply_markup can be inline_keyboard dict."""
    payload: Dict[str, Any] = {
        "chat_id": _chat_id(chat_id),
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
        "disable_notification": disable_notification,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("sendMessage", payload)


@mcp.tool()
def edit_post(
    message_id: int,
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
) -> Dict[str, Any]:
    """Edit a previously published Telegram post."""
    return _post(
        "editMessageText",
        {
            "chat_id": _chat_id(chat_id),
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        },
    )


@mcp.tool()
def delete_post(message_id: int, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete a post by message_id."""
    result = _post(
        "deleteMessage",
        {
            "chat_id": _chat_id(chat_id),
            "message_id": message_id,
        },
    )
    return {"deleted": result, "message_id": message_id, "chat_id": _chat_id(chat_id)}


@mcp.tool()
def pin_post(
    message_id: int,
    chat_id: Optional[str] = None,
    disable_notification: bool = True,
) -> Dict[str, Any]:
    """Pin a Telegram post in the channel."""
    result = _post(
        "pinChatMessage",
        {
            "chat_id": _chat_id(chat_id),
            "message_id": message_id,
            "disable_notification": disable_notification,
        },
    )
    return {"pinned": result, "message_id": message_id, "chat_id": _chat_id(chat_id)}


@mcp.tool()
def publish_photo_post(
    photo_url: str,
    caption: str = "",
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Publish a photo post using a public image URL. reply_markup can be inline_keyboard dict."""
    payload: Dict[str, Any] = {
        "chat_id": _chat_id(chat_id),
        "photo": photo_url,
        "caption": caption,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("sendPhoto", payload)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
