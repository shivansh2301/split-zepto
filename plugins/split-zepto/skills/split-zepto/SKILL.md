---
name: split-zepto
description: Split Zepto grocery orders fairly between flatmates. Fetches the user's own Zepto orders, sorts items into shared pools (Kitchen, House) or personal, accounts for who was home, and writes a private CSV plus a shareable CSV of each person's share. Use when the user asks to split, share or divide Zepto or grocery costs with roommates or flatmates, asks who owes what for groceries, or wants to see or change their split preferences. Needs the Zepto connector and the ability to run Python.
---

# Split Zepto orders with flatmates

You help one person (the **buyer**, called `ME`) split the Zepto orders *they* placed with the people they live with. Each flatmate runs this skill for their own orders.

Explain the model to users with `references/HOW-IT-WORKS.md` (Category → Pool → Participation → Deny). Read it once per session before your first explanation.

## Privacy rules: non-negotiable
1. **Store no personal data.** No names, addresses (not even flat numbers), phone numbers, emails or payment details. The only location kept is the 6-digit delivery **pincode**.
2. **People are short-names** of 2–3 capital letters (AK, PS). If the user types a full name, suggest initials, and never write the full name anywhere.
3. **Never repeat, summarize or store addresses** you see in Zepto responses, and never save raw tool responses.
4. **Never name personal items** in chat, questions, rules or shared files unless the user explicitly asks to see them this time. Talk about them as counts and amounts ("21 items, ₹6,732, defaulted to you").
5. **Personal decisions are saved only as unreadable keys** (the scripts do this). Never add a rule whose pattern names a sensitive personal product. Tighten a shared pattern instead.
6. **Outputs stay local.** Only `zepto_shared.csv` is meant to be shared, and the user shares it themselves.

## What you need
- **Zepto connector tools:** `list_order_history` and `get_order_detail`. Their names may carry a prefix. If they're missing, tell the user how to connect Zepto on their app:
  - **Claude:** Customize → Connectors
  - **Claude Code:** `/mcp`
  - **ChatGPT:** Apps
  - **Codex:** `config.toml`

  Then stop.
- **Python 3:** used to run the scripts in `scripts/`.
- **Data folder:** `$SPLIT_ZEPTO_HOME`, or else `~/split-zepto/`. It holds `rules.json`, `data/orders.jsonl` and the output CSVs. Never write inside the skill folder.
  - **In sandboxed apps** (claude.ai, ChatGPT), the folder is temporary. At the end, offer the CSVs, and `rules.json` if the user saved preferences, as downloads, and explain that they can upload `rules.json` next time.

All scripts take `--home <data folder>`. Paths below are relative to this skill folder.

## Asking questions
- **Clickable choices:** use the platform's multiple-choice question tool if there is one (e.g. `AskUserQuestion`). Otherwise use short numbered options in chat.
- **Keep it short:** one question per *category or product*, never per row. At most 5 per run, biggest money first. Put the suggested answer first and mark it "(Recommended)".
- **A list a question depends on goes in its own message, before you ask.** A list written right next to a question box can be hidden behind it.
- **Unanswered items keep their default (personal),** so the buyer pays and nobody else is over-charged.

## Mode 1: run (default)

### Step 1. Load or create the settings
- **If `<home>/rules.json` exists:** say "Using your saved rules (N people, saved <date>). Change anything?" If the answer is no, skip to step 2.
- **Otherwise, first-time setup.** Copy `presets/roommates-india.json` to a working `rules.json`, then ask:
  1. **"Who lives with you?"** Short-names only. `ME` is the user.
  2. **"Who shares the kitchen (food)? Who shares house things (cleaning)?"** Default: everyone, both. Someone who shares only House gets the pool deny `@grocery`.
  3. **"Anything someone doesn't eat or use?"** Options: meat, eggs, dairy, none. Record these as denies. **Meat means `meat_seafood` and `meat_masala`.**
  4. **"Anyone not home for part of the period?"** This includes not having moved in yet. Record inclusive date ranges; `null` means an open start or end.

  Fill `buckets.grocery.members` and `buckets.household.members`, plus `denies` and `absences`. For the format, read `references/RULESET.md`.

### Step 2. Choose the period
- **Default:** from the day after the last run's end (`last_run_to` in `rules.json`), or else the last 30 days.
- **Ask:** `[That period (Recommended)] [Last month] [Custom dates]`.

### Step 3. Fetch orders
Follow `references/FETCH.md` exactly. It covers paging, when to stop, which orders need details, and the one-line normalized format (pincode only, never the address).
- Append new orders to `<home>/data/orders.jsonl`. The build step removes duplicates.
- Keep the user posted every few pages ("Fetched 40 orders, back to 12 Aug…").
- **Home pincode:** if `review_flags.home_pincode` is empty, set it to the most common pincode among the fetched orders. Don't ask about it.

### Step 4. Build
```bash
python3 scripts/build_split.py --home <home> --from YYYY-MM-DD --to YYYY-MM-DD
```
If it prints total mismatches, re-fetch those orders. Something was transcribed wrong.

### Step 5. Show the result
- **Per-person table:** what each person owes the buyer, per pool.
- **Flags:** "delivered to a different address", "refunded", "high-value shared". Shared item names are fine to mention here.
- **Unlisted items:** only as a count and amount.
- **File paths:**
  - `zepto_shared.csv`: shareable
  - `zepto_orders.csv`: private, everything
  - `zepto_review.csv`: private, view-only, rows to check first

### Step 6. Review questions (a few, grouped)
**Build the queue:**
1. **Flagged shared rows:** e.g. "The 12 Jun order went to a different address. Onion + potato (₹54): split or yours?"
2. **Items that look shared but no rule matched** (a partial match on a shared word): "Is makhana shared?"
3. **One consent question about unlisted items:** "N items (₹X) defaulted to you. Look through them? `[No, they're mine (Recommended)] [Yes, show them]`." Show names only if the user says yes. Afterwards offer: "Save these as confirmed yours (unreadable keys) so they aren't asked again?"

**For each answer:**
1. Write a small decisions CSV (`order_id,item_name,decision,scope`). Decisions are `P` personal, `G` Kitchen or `H` House. Scope is `1` for this order only, or `all` for every purchase. Leave `order_id` empty when the scope is `all`.
2. **Dry run:** run `python3 scripts/apply_review.py <decisions.csv> --home <home>` and show which rows change and each person's total before → after.
3. Ask `[Save to my rules (Recommended)] [Just this run]`.
   - **Save:** rerun with `--apply`.
   - **Just this run:** apply it to a copy (`--rules <copy> --apply`), so the saved `rules.json` doesn't change.

**Decisions about a kind of item** (e.g. "all buttermilk is Kitchen") become a new or edited rule in `rules.json`, not a per-item decision. Before saving, show every purchase the rule would catch.

### Step 7. Save and finish
- **First run:** ask "Save these as your rules for next time?". If the answer is no, delete the working `rules.json` at the end.
- **If saving:** set `last_run_to`.
- **Offer a line to paste in the flat chat** alongside `zepto_shared.csv`:
  `ME · <from>–<to> · shared items ₹<total> · <n> items · sha256:<first 12 chars of the file's sha256>`

## Mode 2: prefs ("show my preferences")
- Run `python3 scripts/show_prefs.py --home <home>` and relay its plain-language output.
- Use `--reveal` only if the user asks to see their hidden "only mine" items. It prints them locally, and you don't repeat them unless asked.

## Mode 3: change ("change my preferences")
**Ask:** "What do you want to change?"
- `[Who shares a kind of item]`: pick a category → pool or personal, whoever's home or always
- `[One item]`: shared, mine or some of us; just this order or always
- `[Away dates]`
- `[People / who denies what]`
- `[Undo a decision]`

**Then:** edit `rules.json` (see `references/RULESET.md`), rebuild, show each person's total before → after, and confirm.

## Contributing back (optional, only if the user asks)
- `python3 scripts/export_suggestions.py --home <home>` writes `contribution.json`, which contains only generic shared-item patterns.
- Ask the user to read it before they share it anywhere. See `CONTRIBUTING.md` in the repo.
