# split-zepto

Split Zepto grocery orders with your flatmates, fairly and privately, just by asking your AI assistant.

> "Split my Zepto orders from last month with my flatmates."

- **Automatic:** vegetables, rice, milk and cleaning supplies are split among whoever was home. Your snacks and personal items stay yours.
- **Simple:** a few click-to-answer questions, then you get a file to share with your flat.
- **Private:** your personal items are never named, people are just short-names (like AK, PS), and your data stays on your machine.

Works with **Claude** (web, desktop, Claude Code), **Codex** and **ChatGPT** (Business, Enterprise, Edu). You need your own Zepto account connected to the assistant.

---

## Install

Pick the app you use. Each option takes about 2 minutes.

### Claude: claude.ai or the Claude desktop app (Pro, Max, Team, Enterprise)
1. Go to **Customize → Plugins → Add marketplace** and paste: `shivansh2301/split-zepto`
2. Find **split-zepto** and click **Install**.
3. On the plugin's **Connectors** tab, click **Connect** next to **Zepto** and log in with your Zepto account. The plugin includes Zepto's official connector.
4. In a chat, say *"split my Zepto orders with my flatmates"*.

*No GitHub?* Download `split-zepto-plugin.zip` from the [Releases](../../releases) page and use **Customize → Plugins → Upload plugin**.

### Claude Code
```text
/plugin marketplace add shivansh2301/split-zepto
/plugin install split-zepto@split-zepto
/mcp            ← log in to Zepto once (the plugin includes Zepto's connector)
```
Then ask *"split my Zepto orders"*, or type `/split-zepto:split-zepto`.

### Codex
```text
$skill-installer shivansh2301/split-zepto/plugins/split-zepto/skills/split-zepto
```
Or download `split-zepto-skill.zip` from [Releases](../../releases) and unzip it into `~/.agents/skills/`.

Then add Zepto's official server to `~/.codex/config.toml` (this needs Node.js) and restart Codex:
```toml
[mcp_servers.zepto]
command = "npx"
args = ["-y", "mcp-remote", "https://mcp.zepto.co.in/mcp"]
```

### ChatGPT (Business, Enterprise, Healthcare, Edu workspaces)
1. Download `split-zepto-skill.zip` from [Releases](../../releases).
2. In ChatGPT, open **Skills → Create → Upload** and choose the zip.
3. Connect Zepto. Zepto's ChatGPT app is **in beta**. Until it's public: **Settings → Apps → Advanced settings → Developer Mode → Create app**, with URL `https://mcp.zepto.co.in/mcp`, then log in.
4. Ask *"split my Zepto orders with my flatmates"*.

*ChatGPT Free, Plus and Pro don't support skills yet.*

---

## What happens when you run it
1. **First time only:**
   - pick who you live with (short-names)
   - who shares food, and who shares cleaning and home items
   - anything someone doesn't eat
   - any away dates
2. **It fetches your orders** for the period you choose.
3. **It shows who owes what,** plus anything worth a second look.
4. **It asks a few questions** about new items. Each answer shows how everyone's total changes before you save it.
5. **Your files:**
   - **`zepto_shared.csv`:** shared items only. Send this to your flat.
   - **`zepto_orders.csv`:** everything you bought. Private.

**Later runs** usually take one or two questions.

**Also:** *"show my split preferences"*, *"change my split preferences"*.

## How it decides who pays
Each item goes through four steps: **Category → Pool → Participation → Deny**. The full explanation, with examples, is in [HOW-IT-WORKS.md](plugins/split-zepto/skills/split-zepto/references/HOW-IT-WORKS.md).

## Privacy in one paragraph
- **What's stored:** short-names only, no real names. No addresses or phone numbers; the only location kept is the delivery pincode, used to flag orders sent somewhere else.
- **Personal items:** never named in rules, questions or shared files. Anything that isn't clearly shared defaults to you.
- **Where it lives:** your settings stay in `~/split-zepto/` on your machine. "Only mine" decisions are stored as unreadable codes.
- **The AI:** while fetching orders, it does see the order details, because that's how the Zepto connection works. It never repeats or stores them beyond the above.

## Help improve it
Teach it new shared-item categories anonymously: see [CONTRIBUTING.md](CONTRIBUTING.md).

## For maintainers
- **Repo layout:**
  - `.claude-plugin/marketplace.json`: the repo is a Claude marketplace
  - `plugins/split-zepto/`: the plugin
  - `…/skills/split-zepto/`: the portable skill, the same folder for Claude, Codex and ChatGPT
- **Build release zips:** `python3 tools/package.py` writes them to `dist/` and refuses to package personal data files.
- **Validate:** `claude plugin validate .`
- **Design notes:** [docs/system-plan.md](docs/system-plan.md)

## License
[GPL-3.0-or-later](LICENSE). You may use, change and share this, and anything you distribute that's based on it must stay open under the same license.
