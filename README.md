# MCP Servers · marketing & ops toolkit for AI agents

> A collection of **7 custom Model Context Protocol (MCP) servers** that wire marketing platforms into LLM-agent loops. Built so an agent (Claude Code, Claude Desktop, etc.) can run ad campaigns, read analytics, publish posts, and check SEO health directly — without humans clicking buttons.

If you don't know what MCP is, [start here](https://modelcontextprotocol.io/) — it's Anthropic's open protocol for plugging tools into LLM apps.

## What's inside

| Server | What it exposes to the agent |
|---|---|
| [`clickru/`](./clickru/) | Click.ru API — Telegram Ads, VK Ads, Yandex.Direct campaigns, balances, reports, bid manager |
| [`yadirect/`](./yadirect/) | Yandex.Direct — create/pause campaigns, manage keywords, bids, ad copy |
| [`yandex-webmaster/`](./yandex-webmaster/) | Yandex.Webmaster — indexing, top queries, sitemap, recrawl, problem detection |
| [`gsc/`](./gsc/) | Google Search Console — top queries, pages, country breakdown, indexed status |
| [`youtube/`](./youtube/) | YouTube Data API — videos, channels, comments, transcripts, trending |
| [`vk/`](./vk/) | VK Wall API — publish, edit, pin posts, upload photos, stats |
| [`edaru-telegram/`](./edaru-telegram/) | Telegram Bot API — publish/edit/delete/pin posts in configured channels |

Together they cover the **full growth stack** for a typical Russian-market product: paid ads (Direct + Telegram Ads + VK Ads via Click.ru), organic search (Yandex Webmaster + GSC), and content distribution (VK + Telegram).

## Why this matters

In 2026 the bottleneck of growth isn't "what to do" — agents can plan. It's the **glue between AI plans and platform APIs**. These servers are that glue.

A typical workflow an LLM-agent can now run unattended:

1. `gsc.get_top_queries('edaru.su')` → see which keywords are climbing
2. `yandex-webmaster.get_top_queries('edaru.su')` → cross-check on Yandex
3. `yadirect.get_keywords('campaign_id=...')` → see which keywords we already bid on
4. Decide on new keywords to add → `yadirect.add_negative_keywords(...)`, adjust bids
5. `vk.post_to_wall(...)` and `edaru-telegram.publish_post(...)` to push fresh content
6. Next day: `clickru.get_campaign_stats(...)` to see what worked

All without a marketer touching the console.

## Setup

Each server is a standalone Python process. Common pattern:

```bash
cd <server>/
pip install -r requirements.txt   # if present
cp .env.example .env              # fill in your credentials
python3 server.py
```

For Claude Desktop / Claude Code, add to your MCP config (`~/.config/claude/mcp.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "yadirect": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/yadirect/server.py"],
      "env": { "YANDEX_DIRECT_TOKEN": "..." }
    }
  }
}
```

## Credentials needed

| Server | What to get |
|---|---|
| `clickru` | Click.ru API key + account ID (in the Click.ru dashboard) |
| `yadirect` | Yandex.Direct OAuth token via [oauth.yandex.ru](https://oauth.yandex.ru) |
| `yandex-webmaster` | Same OAuth flow as Direct, with `webmaster:hostinfo,webmaster:verify` scopes |
| `gsc` | Google service account JSON with Search Console access |
| `youtube` | YouTube Data API v3 key (Google Cloud Console) |
| `vk` | VK group access token (admin rights) |
| `edaru-telegram` | Telegram bot token (BotFather) + chat ID |

`yandex-webmaster/oauth_helper.py` includes a working OAuth flow if you want to grab tokens locally.

## Tech stack

- Python 3.10+ · stdlib + `requests`
- `mcp` Python SDK
- One process per platform — easy to enable/disable independently

## Roadmap

- Telegram Ads MCP (independent of Click.ru, native API)
- Plausible / Yandex.Metrika real-time MCP (currently only reports)
- One-shot CLI wrappers so you can call any of these without an MCP host

---

**Author:** Sergey Krinitsyn · [putksebe.su/cv](https://putksebe.su/cv) · sergeykrin98@gmail.com
