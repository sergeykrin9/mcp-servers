<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a1d,50:c08a52,100:1a1a1d&height=200&section=header&text=MCP%20Servers&fontSize=52&fontColor=f5f1e8&fontAlignY=38&desc=Russian-market%20marketing%20%26%20ops%20toolkit%20for%20Claude%20%2F%20Cursor%20%2F%20Windsurf&descSize=14&descAlignY=62" alt="MCP Servers" />

<div align="center">

<p>
  <a href="https://github.com/SergeyKrin9/mcp-servers/stargazers"><img src="https://img.shields.io/github/stars/SergeyKrin9/mcp-servers?style=for-the-badge&color=c08a52&logo=github&labelColor=1a1a1d"></a>
  <a href="https://github.com/SergeyKrin9/mcp-servers/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-c08a52?style=for-the-badge&labelColor=1a1a1d"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-c08a52?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a1d">
  <img src="https://img.shields.io/badge/MCP-protocol-FF6B35?style=for-the-badge&logo=anthropic&logoColor=white&labelColor=1a1a1d">
</p>

<sub>🐍 Python · 🇷🇺 Russian market · 🎖️ The only unified RU-platform MCP bundle · 🤖 7 servers</sub>

</div>

> [!IMPORTANT]
> **The only unified MCP toolkit for Russian-market platforms.** Yandex.Direct, Yandex.Webmaster, Yandex.Metrika (via energyboost), Google Search Console, YouTube, VK, Telegram, Click.ru. No equivalent exists in `awesome-mcp-servers`. If you do SEO/SMM/PPC for a Russian audience and use Claude — this is your missing kit.

A collection of **7 custom Model Context Protocol (MCP) servers** that wire marketing platforms into LLM-agent loops. Built so an agent (Claude Code, Claude Desktop, Cursor, Windsurf) can run ad campaigns, read analytics, publish posts, and check SEO health directly — without humans clicking buttons.

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

## ⚡ Quickstart (3 steps)

**1. Clone & install:**

```bash
git clone https://github.com/SergeyKrin9/mcp-servers.git
cd mcp-servers/yadirect            # or any other server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt    # if present
cp .env.example .env               # fill in your credentials
```

**2. Wire into your AI host:**

<details>
<summary><strong>Claude Desktop / Claude Code</strong> (<code>~/Library/Application Support/Claude/claude_desktop_config.json</code>)</summary>

```json
{
  "mcpServers": {
    "yandex-direct": {
      "command": "/abs/path/to/mcp-servers/yadirect/.venv/bin/python3",
      "args": ["/abs/path/to/mcp-servers/yadirect/server.py"],
      "env": { "YANDEX_DIRECT_TOKEN": "your-token" }
    }
  }
}
```
</details>

<details>
<summary><strong>Cursor</strong> (<code>~/.cursor/mcp.json</code>) — same JSON shape</summary>

```json
{
  "mcpServers": {
    "vk": {
      "command": "/abs/path/to/.venv/bin/python3",
      "args": ["/abs/path/to/mcp-servers/vk/server.py"],
      "env": { "VK_TOKEN": "your-token", "VK_GROUP_ID": "123456" }
    }
  }
}
```
</details>

<details>
<summary><strong>Windsurf</strong> (Settings → MCP Servers → Add) — same JSON shape</summary>

Identical config — Windsurf uses the same MCP server format.
</details>

**3. Test the loop.** Open a fresh Claude chat and ask:

> *"Show me the top 5 search queries for edaru.su from Google Search Console for the last 7 days, then check the same in Yandex.Webmaster, then queue new keywords matching the gaps to my Yandex.Direct campaign."*

If everything's wired right, Claude will run `gsc.get_top_queries → yandex-webmaster.get_top_queries → yadirect.add_keywords` in one tool loop — without you opening a single dashboard.

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

## ⭐ Star history

<a href="https://www.star-history.com/#SergeyKrin9/mcp-servers&Date">
  <img src="https://api.star-history.com/svg?repos=SergeyKrin9/mcp-servers&type=Date" alt="Star History" />
</a>

## 📚 Related work

- **[agnis-workflow](https://github.com/SergeyKrin9/agnis-workflow)** — the methodology that uses these MCP servers as first-class tools
- **[broker-reels](https://github.com/SergeyKrin9/broker-reels)** — production application: AI text-to-video for real estate marketing
- **[awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)** — the canonical MCP catalog (no Russian-market entries yet — PR welcome)

---

<div align="center">

**Author:** [Sergey Krinitsyn](https://putksebe.su/cv) · sergeykrin98@gmail.com · [GitHub](https://github.com/SergeyKrin9)

<sub>If you ship to a Russian audience and use Claude — drop a ⭐. It tells me to keep adding servers.</sub>

</div>
