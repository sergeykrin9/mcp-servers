<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a1d,50:c08a52,100:1a1a1d&height=200&section=header&text=MCP%20Servers&fontSize=52&fontColor=f5f1e8&fontAlignY=38&desc=Russian-market%20marketing%20%26%20ops%20toolkit%20for%20Claude%20%2F%20Cursor%20%2F%20Windsurf&descSize=14&descAlignY=62" alt="MCP Servers" />

<div align="center">

<p>
  <a href="https://github.com/SergeyKrin9/mcp-servers/stargazers"><img src="https://img.shields.io/github/stars/SergeyKrin9/mcp-servers?style=for-the-badge&color=c08a52&logo=github&labelColor=1a1a1d"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-c08a52?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a1d">
  <img src="https://img.shields.io/badge/MCP-protocol-FF6B35?style=for-the-badge&logo=anthropic&logoColor=white&labelColor=1a1a1d">
</p>

<sub>🐍 Python · 🇷🇺 Russian market · 🤖 8 server directories</sub>

</div>

> [!IMPORTANT]
> Integrations for advertising, search analytics, and social publishing. Each server requires its own platform setup and permissions.

A collection of **8 custom Model Context Protocol (MCP) server directories** that wire marketing platforms into LLM-agent loops. Built so an agent (Claude Code, Claude Desktop, Cursor, Windsurf) can run ad campaigns, read analytics, publish posts, and check SEO health directly — without humans clicking buttons.

If you don't know what MCP is, [start here](https://modelcontextprotocol.io/) — it's Anthropic's open protocol for plugging tools into LLM apps.

## What's inside

| Server | What it exposes to the agent |
|---|---|
| [`linkedin/`](./linkedin/) | LinkedIn profile and publishing tools; see its own README |
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

Start by listing the selected server’s tools. Review their parameters before using real accounts: several tools create campaigns or publish content.

## ⚡ Quickstart (3 steps)

**1. Clone & install:**

```bash
git clone https://github.com/SergeyKrin9/mcp-servers.git
cd mcp-servers/yadirect            # or any other server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt    # if present
# yadirect reads YANDEX_DIRECT_TOKEN from the process environment.
# Configure it in your host; no .env.example or dotenv loader is provided here.
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

**3. Check tool discovery.** Ask your host to list the configured server’s tools without invoking them. This checks MCP registration without making advertising or publishing requests. API integration checks require a separate test account and are not covered by this step.

## Credentials needed

| Server | What to get |
|---|---|
| `linkedin` | LinkedIn access token; see `linkedin/README.md` |
| `clickru` | Click.ru API key + account ID (in the Click.ru dashboard) |
| `yadirect` | Yandex.Direct OAuth token via [oauth.yandex.ru](https://oauth.yandex.ru) |
| `yandex-webmaster` | Same OAuth flow as Direct, with `webmaster:hostinfo,webmaster:verify` scopes |
| `gsc` | Google service account JSON with Search Console access |
| `youtube` | YouTube Data API v3 key (Google Cloud Console) |
| `vk` | VK group access token (admin rights) |
| `edaru-telegram` | Telegram bot token (BotFather) + chat ID |

`yandex-webmaster/oauth_helper.py` includes a working OAuth flow if you want to grab tokens locally.

## GSC configuration migration

The GSC server no longer falls back to a machine-specific credential path. Set `GSC_SERVICE_ACCOUNT_KEY` in the environment of the MCP server process to the absolute path of **your existing** service-account JSON file:

```json
{
  "env": {
    "GSC_SERVICE_ACCOUNT_KEY": "/absolute/path/to/your-existing-service-account.json"
  }
}
```

Merge this `env` entry into your existing GSC server configuration and restart that server. Replace the placeholder with your own local path; do not paste the JSON file contents into the configuration or commit them. This change creates no credentials and grants no new permissions. The existing service account must already have access to the Search Console property. If the variable is missing, the server reports a configuration error when a GSC tool is called.

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
- **[broker-reels](https://github.com/SergeyKrin9/broker-reels)** — Python pipeline for real estate videos, with an offline demo
- **[awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)** — the canonical MCP catalog

---

<div align="center">

**Author:** [Sergei Grin](https://putksebe.su/cv) · sergeykrin98@gmail.com · [GitHub](https://github.com/SergeyKrin9)

<sub>If you ship to a Russian audience and use Claude — drop a ⭐. It tells me to keep adding servers.</sub>

</div>
