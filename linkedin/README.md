# LinkedIn MCP server

> Publish posts and read your own profile from LinkedIn via Claude Code / Cursor / Windsurf using the official LinkedIn API.

## What this gives you

| Tool | Does what |
|---|---|
| `linkedin.get_my_profile` | Returns your basic profile (id, name, email, URN) |
| `linkedin.publish_post(text)` | Publishes a text post to your feed (visibility `PUBLIC` or `CONNECTIONS`) |
| `linkedin.get_post_stats(post_urn)` | Likes/comments/shares for one of your own posts |
| `linkedin.draft_post_from_repo(repo_url, hook_line)` | Drafts (does not publish) a repo-promotion post |

## What this does NOT do (be honest)

- ❌ Search connections / send connection invites
- ❌ Send InMail or DMs
- ❌ Read other users' profiles or posts
- ❌ Scrape data (against ToS)

Those require LinkedIn Recruiter Lite / Sales Navigator / Marketing Developer Platform — all paid + formal app review. For now, LinkedIn's web UI remains the right tool for outreach.

## Setup (15 minutes one-time)

### 1. Create a LinkedIn app

1. Go to https://www.linkedin.com/developers/apps
2. **Create app** → fill in:
   - **App name:** `Personal MCP` (or whatever)
   - **Company:** pick or create a "personal" page
   - **App logo:** any image, doesn't matter
   - **Legal Agreement:** check the box
3. Open your new app → **Products** tab → request:
   - **Share on LinkedIn** (auto-approved, gives `w_member_social`)
   - **Sign In with LinkedIn using OpenID Connect** (auto-approved, gives `openid profile email`)
4. **Auth** tab:
   - Add redirect URL: `http://localhost:8765/callback`
   - Copy **Client ID** and **Client Secret** (you'll need both)

### 2. Install + configure

```bash
cd mcp-servers/linkedin
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — paste Client ID + Client Secret
```

### 3. Get an access token

```bash
python3 oauth_helper.py
```

The script opens your browser, you authorize the app, the callback prints the access token. Copy that into `.env` as `LINKEDIN_ACCESS_TOKEN`.

Access tokens last **60 days**. After expiry, re-run `oauth_helper.py`.

### 4. Wire into Claude

Drop into `~/Library/Application Support/Claude/claude_desktop_config.json` (or your project `.mcp.json`):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "/abs/path/to/mcp-servers/linkedin/.venv/bin/python3",
      "args": ["/abs/path/to/mcp-servers/linkedin/server.py"],
      "env": {
        "LINKEDIN_ACCESS_TOKEN": "AQVx..."
      }
    }
  }
}
```

Restart Claude Desktop. Test:

> *"Publish this LinkedIn post: [your text]. Visibility public."*

Claude calls `linkedin.publish_post` and confirms with the URL.

## What you can ask Claude to do once it's wired

- *"Draft a LinkedIn post for my agnis-workflow repo with the hook 'after 8 months shipping AI products solo'."* → it calls `draft_post_from_repo`, returns the draft.
- *"Publish that draft."* → it calls `publish_post`.
- *"How did the post from yesterday do?"* → it pulls the URN from history and calls `get_post_stats`.

## Limitations to know about

- **Rate limit:** ~150 posts per day per app (you'll never hit this manually).
- **Token expiry:** 60 days. The helper re-issues — just re-run.
- **OpenID Connect:** uses LinkedIn's newer auth flow, not the old legacy `r_emailaddress` scope.

## Future tools (planned, not built)

These are honest limitations of the LinkedIn API. If LinkedIn changes policy or you upgrade to a paid plan:

- `linkedin.search_jobs(query, location)` — possible via the **Jobs API** (paid Marketing Developer Platform)
- `linkedin.send_invite(profile_urn, note)` — possible via **Recruiter Lite API**
- `linkedin.search_people(query)` — possible via **Sales Navigator API**

I won't add scraping-based versions of these. Risk of LinkedIn ban is too high.

---

**Part of [SergeyKrin9/mcp-servers](https://github.com/SergeyKrin9/mcp-servers)** · MIT licensed · sergeykrin98@gmail.com
