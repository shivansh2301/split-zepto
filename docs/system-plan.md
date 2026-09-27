# House Split: system plan

> **Implemented layout (v0.1):** see README → *For maintainers*. The skill lives in `plugins/split-zepto/skills/split-zepto/`, the settings format is `references/RULESET.md`, and "deny" is implemented as `denies` in the settings file. This document keeps the design reasoning.

**Goal:** a skill that any flat can set up in about 10 minutes and run whenever needed. It pulls orders from Zepto (more apps later) and applies the house's own rules. Everyone gets a split of what they bought: each shared item, who it's split among, and each person's share. **Scope: split calculation only.** Who-pays-whom and settlement are out of scope.

The current Zepto setup (`rules.json`, `build_split.py`) is the prototype. This plan generalises it.

---

## 1. Core components

| # | Component | What it answers | In the example flat |
|---|---|---|---|
| 1 | **People** | Who lives here? | ME, AK, PS, RJ |
| 2 | **Calendar** | Who was *not home*, and when? This includes before moving in and after moving out. | `absences` (PS 5–25 Jun, AK 10–14 Jul, RJ until 31 Mar) |
| 3 | **Categories** | What kind of item is this? | Regex `rules` → `category` (fruit_veg, staples, dairy, …) |
| 4 | **Pools** | Which group shares this category? | `buckets`: grocery = ME+AK+PS, household = all 4, meat = ME+AK, personal = buyer |
| 5 | **Split policies** | How is a category split within its pool? | **default: whoever was home**; `always` only for long-lasting pantry (rice, atta, ghee, oil, dal, spices) |
| 6 | **Preferences** | Individual opt-outs and "that's mine" items | "PS doesn't share meat", "tortilla/tissue/parota are ME's", "Diet Coke is shared" |
| 7 | **Exceptions** | One-off corrections for a single purchase | `overrides.by_order_item` (5 meat orders → personal) |
| 8 | **Money policy** | Fees, discounts, refunds, rounding, cancelled orders | Fees/discounts pro-rata by line total, refunds subtracted, cancelled orders excluded |
| 9 | **Buyer** | Whose orders are being split? | the person running the skill, on their own Zepto account |
| 10 | **Sources** | Where do orders come from? | Zepto MCP → `data/orders.jsonl` (normalized) |
| 11 | **Review loop** | How does the house decide unknowns? | review queue → rule or one-off (plan §"Collecting ME's preferences") |
| 12 | **Outputs & privacy** | Who sees what? | private CSV for the buyer, shared CSV without personal items |

Your four headings fit into this:
- **users** = People and Calendar
- **categories** = Categories
- **split preferences** (Diet Coke, veggies, staples) = Pools and Policies
- **non-split preferences** (meat) = Preferences: opt-outs, plus "mine" items

---

## 2. One design change: *derive* pools instead of hand-writing them

Today `meat = [ME, AK]` is a separate bucket. That doesn't scale. Every new diet or habit would need a new bucket.

Generic version: there's one kitchen pool, and people **opt out** of categories.

```
kitchen pool = everyone living here
meat         → kitchen minus people who opted out of meat   (PS opts out) → ME+AK
diet coke    → kitchen                                        (house preference)
cold drinks  → buyer only                                     (default policy)
```

So "who shares X on date D" is computed in this order:

1. **Pool:** the category's pool (`kitchen`, `house`, or `buyer`).
2. **Presence:** remove anyone not home on D. This is the default for everything, including Diet Coke and household items. It's skipped only for categories marked `always` (long-lasting pantry). "Not home" covers short trips *and* "hadn't moved in yet", so there's no separate membership concept.
4. **Opt-outs:** remove anyone who opted out of the category or item.
5. **Exceptions:** an exception on this exact purchase overrides everything above.

Every flatmate can state their own preferences ("I don't eat meat", "oat milk is mine") without anyone redesigning buckets.

---

## 3. Config: one `house.json` per flat

This is our current house, expressed in the generic format:

```json
{
  "house": "HOME",
  "currency": "INR",
  "timezone": "Asia/Kolkata",

  "people": {
    "ME": {},
    "AK":   {"away": [["2026-07-10", "2026-07-14"]]},
    "PS":   {"away": [["2026-06-05", "2026-06-25"]],
             "opt_out": ["meat", "meat_masala"]},
    "RJ":   {"away": [[null, "2026-03-31"]],
             "opt_out": ["@kitchen"]}
  },

  "pools": {
    "house":   "everyone",
    "kitchen": "everyone",
    "buyer":   "buyer"
  },

  "category_policy": {
    "_default":   {"mode": "presence"},
    "pantry":     {"pool": "kitchen", "mode": "always"},
    "spices":     {"pool": "kitchen", "mode": "always"},
    "fruit_veg":  {"pool": "kitchen"},
    "dairy":      {"pool": "kitchen"},
    "bakery":     {"pool": "kitchen"},
    "eggs":       {"pool": "kitchen"},
    "meat":       {"pool": "kitchen"},
    "cleaning":   {"pool": "house"},
    "home":       {"pool": "house"},
    "sweets":     {"pool": "buyer"},
    "cold_drinks":{"pool": "buyer"}
  },

  "item_preferences": [
    {"match": "diet coke",                  "pool": "kitchen", "note": "house pref"},
    {"match": "parota|tortilla|tissue|foaming handwash|baking sheets", "pool": "buyer", "by": "ME"},
    {"match": "chicken masala",             "as_category": "meat", "mode": "always"}
  ],

  "exceptions": [
    {"order": "ORDER0001", "item": "Licious Goat Curry Cut (Mini Pack)", "pool": "buyer"}
  ],

  "money": {"fees": "pro_rata", "discounts": "pro_rata", "refunds": "subtract", "rounding": "paise"}
}
```

Here's where each part of today's `rules.json` goes:

| Today | Generic |
|---|---|
| `buckets.grocery.members` | `pools.kitchen` = everyone, minus RJ's opt-out `@kitchen` |
| `buckets.meat` | derived: kitchen minus `PS.opt_out: meat` |
| `buckets.personal` | `pool: buyer` (works when others also order) |
| default split (whoever was home) / `always: true` | `mode: presence` (default) / `mode: always` |
| `absences` (incl. RJ `[null, 2026-03-31]`) | `people.X.away` |
| `personal_pref`, `diet_coke`, `meat_masala` rules | `item_preferences` (with a `by` field where it's one person's preference) |
| `overrides.by_order_item` | `exceptions` |
| regex `rules` (the category patterns) | a **shared category library** (next section) |

---

## 4. Category library (ships with the skill)

`defaults/categories.json` holds the regex patterns we've already tuned. They cover about 30 categories: fruit_veg, dairy, staples, spices, meat, cleaning, sweets, ice_cream, personal_care and so on, and they classified all 614 delivered item lines in our 6 months of data.

Each house only sets which pool and mode each category uses, which is a short list. It doesn't write patterns unless it wants to. A pattern that still matches nothing goes to the review queue.

The library improves as more flats use it, and house-specific decisions stay in `house.json`.

---

## 5. Scope: split calculation only

The system answers one question: **"For the orders I bought, what is each person's share?"**

**Out of scope:**
- tracking who paid
- running balances
- minimum transfers
- settle-up messages
- marking payments done

People settle however they already do. The split output is the input they settle from.

---

## 6. Sources (adapters → one normalized format)

The normalized order format already exists (`data/orders.jsonl`: order id, date, status, items, fees, discounts, refunds, in paise). Each source only needs a normalizer:

| Source | How |
|---|---|
| Zepto | MCP, read-only (done). Incremental: stop paging at the last order already stored. Keeps only the delivery `pincode` from the address |
| Blinkit / Instamart / BigBasket | MCP if available, else invoice PDF/email parsing |
| Manual | paste-a-receipt, or a CSV row (`date, item, amount`) |

---

## 7. The skill: what it does on each run

```
/house-split setup     one-time onboarding (conversation → house.json)
/house-split           run the split for a date range
/house-split review    resolve the review queue
```

**Setup** (conversational, about 10 questions):
1. Who lives here? Asked as short short-names, with initials suggested and full names never stored. Was anyone not home for part of the period (including not moved in yet)?
2. Who orders from which app and account?
3. Which categories are shared and which are personal? By default, shared items are split among whoever was home. Only long-lasting pantry is split among everyone. Answered by picking from the library defaults.
4. For each person: anything you never share, or anything you opt out of?
5. How should delivery fees be split?

**Each run:**
1. Fetch new orders since the last run, per source.
2. Classify, then apply people, calendar and preferences.
3. Show the review queue, grouped by category, one question per category.
4. Ask "was anyone away this month?" and add those dates to the calendar.
5. Build the outputs and show a diff against last month's rules.

**Review loop:** this is already written down in the current plan and saved in memory.
- **Row labels:** people paste rows under a label: `personal`, `/3`, `only X+Y`.
- **Exception or preference:** anything called an "exception" becomes a one-off; anything called a "preference" or a category answer becomes a rule.
- **Before applying:** list the side-effects.
- **After the rebuild:** show the changed rows.
- **Record-keeping:** every decision gets a `note`, who decided it, and the date.

---

## 8. Outputs & privacy

| Output | Audience | Contains |
|---|---|---|
| `statements/<person>.csv` | that person | only items they share in, their share per row, total |
| `shared.csv` | whole flat | all shared items with a column per person, no personal items, no order totals |
| `private/<buyer>.csv` | buyer only | everything they bought, including personal items |

**Privacy rules:**
1. **No personal data stored anywhere.** That means files, saved rulesets, agent memory and outputs. Excluded:
   - names
   - addresses (including flat numbers)
   - phone numbers and emails
   - payment details
   - invoice URLs
2. **People are short short-names only,** 2–3 capital letters (e.g. `AK`, `PS`, `RJ`, `ME`).
   - If someone types a full name at setup, the skill suggests initials ("Anita Nair" → `AK`; on a clash, `ANI` or `AN2`). It keeps only the short-name, and the full name is never written down.
   - The runner is `ME` by default.
   - The flat is a short-name too (`HOME`), never an address.
3. **Location is kept only as the delivery `pincode`** (6 digits). The street, building and flat are never stored.
   - The home pincode is one value in the ruleset. Any order to a different pincode gets flagged.
   - An address Zepto hides (`***`) is stored as `pincode: null`.
4. **Addresses in MCP responses:** fetching through the MCP in chat means the model sees the full address in the tool response. That's accepted: it can't be avoided with the current MCP. The rule is to extract only the pincode, never repeat, store or summarize the address, and never store raw responses.
5. **Read-only sources.**
6. **Personal items never leave the buyer's private file.** Flags in the shared file use generic wording (e.g. "delivered to a different address", never the pincode).
7. **Local files by default.** Sharing is an explicit step the house chooses.

**Review flags** (a usability feature, `review_flag` column in both CSVs; it never changes the split, only highlights rows):

| Flag | When | Why it matters |
|---|---|---|
| delivered to a different address | order `pincode` ≠ home pincode | probably a trip or someone else's order; maybe shouldn't be split |
| delivery pincode unknown | `pincode` is null (optional, off by default) | Zepto hid the address |
| high-value shared item | shared item ≥ threshold (default ₹500) | worth a second look before others pay for it |
| refunded | item had a refund | confirm the refund was applied to the split |
| needs a split decision | no rule matched | goes to the review queue |

The summary lists flagged rows grouped by flag, and each flag can be switched on or off in the ruleset.

---

## 9. Skill layout

```
house-split/
  SKILL.md                     workflow + review-loop rules + privacy rules
  scripts/
    split.py                   generalised build_split.py (pools, opt-outs, presence)
    normalize_zepto.py         MCP order JSON → orders.jsonl line (pincode only, no address)
    validate_house.py          schema check with friendly errors
  defaults/
    categories.json            the pattern library
    house.template.json
  houses/<house>/
    house.json
    data/orders.jsonl
    out/<YYYY-MM>/...
```

---

## 10. Build order

1. **Refactor** `rules.json` → `house.json` + `categories.json`. Swap buckets for pools and opt-outs. Output must match today's totals to the paisa (regression test using today's data).
2. **Per-person statements.**
3. **Fetch helper.** Makes in-chat fetching less manual: the model passes each MCP response through a small normalizer that outputs the orders.jsonl line (with pincode only). This means less hand-transcription and fewer mistakes.
4. **Presets + question tree** (§12). Generate `presets/roommates-india.json` from our rules (strip names, dates and exceptions). Test: the tree replay in §12c must reproduce today's totals.
5. **SKILL.md.** Covers onboarding (create/join), each run, and the review loop.
6. *(Later)* **Second source,** manual CSV, if the flat ever wants non-Zepto spends.
7. **Optional:** a shared page where each flatmate edits only their own preferences.

---

## 11. Everyone runs it for themselves

**Decided (2026-09-27):** each flatmate runs the skill on **their own** orders and posts their side of the split. No one needs anyone else's account or private data.

```
ME runs /house-split  →  out/ME-shared.csv   (items ME bought that others share, with each person's share)
AK   runs /house-split  →  out/AK-shared.csv
PS   runs /house-split  →  out/PS-shared.csv
```

- **Two config layers:**
  - **`house.json` (shared):** one copy for the flat. It holds people, not-home dates, what each category means for the house, and **everyone's opt-outs**. Opt-outs belong to the consumer, not the buyer: ME's run must already know that PS doesn't eat meat.
  - **`me.json` (private, per person):** the buyer's own "that's mine" items, one-off exceptions, and account/source settings. Never shared.
- **What gets shared:** only `*-shared.csv` files, which contain no personal items.
- **Sharing the house file:** the first person creates `house.json`. Everyone else **joins** it (copies it in) and only answers questions about themselves.

---

## 12. Onboarding without the burden: presets and a question tree

Nobody should have to think in pools and opt-outs. They answer plain questions, and the skill writes the config.

### 12a. Presets (the prototype flat's rules become the default)
The rules we built are shipped as a named preset, with names, dates and exceptions stripped:

| Preset | For | What it assumes |
|---|---|---|
| **`roommates-india`** (default, = our ruleset) | flats that cook together | **shared items ÷ whoever was home** (veg, fruit, dairy, bread, eggs, cleaning, home); only long-lasting pantry (rice, atta, ghee, oil, dal, spices) ÷ everyone; sweets, snacks, cold drinks, personal care, tissue boxes, fancy handwash → buyer; meat → people who eat meat |
| `share-everything` | couples, very close flats | every food/household item ÷ all; only personal care → buyer |
| `staples-only` | flats that mostly eat separately | only staples + cleaning shared; everything else → buyer |

Setup begins with **"Pick a starting point"**, with `roommates-india` preselected. Most people press Enter and stop there.

### 12b. The question tree (data-driven, few questions)
The skill asks **only about categories this person actually bought**, ordered by spend, using their real item names as examples. Each answer is a click (AskUserQuestion), and the preset's answer is preselected. The rupee amounts below are illustrative. At runtime they come from the person's own orders.

```
Q0  Pick a starting point:  [roommates-india ✓] [share-everything] [staples-only]

Q1  Join a house or create one?
      join   → load house.json, skip to "About you"
      create → "Who lives here?" (short-names only; typed names become suggested initials and aren't kept)

──── About the house (creator only; skipped for joiners) ────
Default for every shared category: split among whoever was home. Only the pantry question (Q2b) defaults to "still pay".
For each category the person bought, biggest spend first, max ~8 questions:
Q2  "Rice, atta, dal (₹2,000 from your orders) are…"
      [Shared by everyone ✓] [Only mine] [Some of us → pick names]
Q2b   if shared:  "If someone's away for a week, do they still pay for these?"
      [Yes, it's a staple ✓] [No, only who's home pays]
Q3  "Vegetables & fruit (₹3,000)…"            [Shared ✓] …  → b: [No, only who's home ✓]
Q4  "Chicken, prawns (₹1,500)…"               [Shared] [Only mine] [Some of us ✓ → pick]
Q5  "Detergent, broom, cleaning (₹1,200)…"    [Shared ✓] … → b: [No, only who's home ✓]
…stop once ≥90% of spend is covered. The rest follows the preset and is listed for later review.

──── About you (everyone, including joiners) ────
Q6  "Anything the house shares that you DON'T eat/use?"   multi-select: [meat] [eggs] [dairy] [none ✓]
Q7  "Your own items that look shared, e.g. you bought Diet Coke 30× — is it…"
      [Mine only] [Shared ✓]      ← asked only for items that sit on a preset boundary
Q8  "Were you not home for part of this period (trip, or not moved in yet)?"   [No ✓] [Yes → date range, open start/end allowed]
```

- **Why it stays short:** defaults come from the preset, and questions cover only categories you actually bought.
- **What gets written:** answers to Q2–Q5 go into the house layer; Q6 and Q8 go into the house file under your name; Q7 goes into `me.json`.
- **Later changes:** the same review loop as today. You paste rows, and the skill turns them into rules or one-offs, shows the side-effects and rebuilds.

### 12c. The example flat, replayed through the tree
This checks that the tree can reproduce everything we set up by hand:

| Our rule | Tree answer that produces it |
|---|---|
| pantry (rice, atta, ghee, oil, dal, spices) ÷3 always | Q2 Shared → Q2b Yes |
| veg/dairy/eggs/paneer ÷ whoever's home | Q3 Shared → Q3b No |
| meat ME+AK | Q4 Shared + PS answers Q6 "meat" |
| chicken masala with meat | preset maps "meat masala" into the meat category (no question) |
| cleaning/Diet Coke ÷ whoever's home; RJ not before 1 Apr | Q5 Everyone (default: only who's home) + RJ's Q8 "not home until 31 Mar" |
| PS/AK away dates | their own Q8 |
| Diet Coke shared, other cold drinks mine | Q7 (Diet Coke sits on the boundary: cold drinks default to "mine") |
| tortilla/parota/tissue mine | Q7, or the later review loop |
| 5 meat orders personal | review loop → one-off exceptions (never asked up-front) |

---

## 13. Sharing the split privately and auditably

**Decided (2026-09-27):**
- **Scope:** the split calculation only. No settlement or ledger.
- **Timing:** run on demand, whenever ME wants or someone asks.
- **Sources:** Zepto only.

**No double-counting between runs:** each run is for a date range (`--from/--to`), and the output file names include that range. Future runs can default `--from` to the day after the previous run's `--to`.

### 13a. Levels of detail
| Level | What others see | Default |
|---|---|---|
| **Summary** | per person, per category totals | always |
| **Detail** | each shared item: date, order id, item, amount, split_among, each person's share | included (house can switch to on-request) |
| **Private** | personal items, order totals, anything not split | never leaves the buyer's machine |

**Disputes:** every detail row carries the Zepto **order id**. The buyer can show that order in the Zepto app, so no receipts are stored anywhere.

### 13b. Where the split files go
| Option | Privacy | Audit trail | Effort |
|---|---|---|---|
| **A. Flat WhatsApp group + fingerprint line** *(recommended)* | E2E-encrypted, in an existing chat | chat history + sha256 fingerprint posted with each file, so later edits are detectable | none |
| B. Shared Drive/OneDrive folder | provider can read | version history | low |
| C. Private git repo | host can read | full diff history | high for non-developers |
| D. Hosted shared page | data leaves your machines (against local-only rule) | edit history | lowest, not recommended |

**The run prints a one-line receipt to post with the file:**
`ME · 27 Mar–26 Sep · shared items ₹<total> · <n> items · sha256:<fingerprint>`

## 14. State: stateless by default, memory only on request

**Decided (2026-09-27).**

- **Stateless by default:** a run takes the preset plus this run's answers, and produces the split. Nothing about preferences is written anywhere. Next time, it starts again from the preset.
- **Saved preferences are opt-in.** At the end of setup, and after any review round, the skill asks: *"Save these as your rules for next time?"* `[Yes] [No, just this run]`. If yes, it writes a single **ruleset file** on the user's own machine, e.g. `~/.house-split/<house>/rules.json`, or the agent's memory if the host offers it. The file holds:
  - the chosen preset
  - the tree answers
  - item/category preferences
  - who opts out of what
  - not-home dates
  - one-off exceptions
- **Next run with a saved ruleset:** "Using your saved rules (preset roommates-india + 14 preferences, saved 27 Sep). Change anything?" If the answer is no, it runs with zero questions.
- **The review loop writes back into the saved ruleset.** When the user pastes rows or answers review questions, the change is shown as a diff against the saved file, with every purchase it affects. Once confirmed, it's written back.
  - Each entry gets a `note` and a date, so the file is also the audit log of the user's decisions.
  - With no saved file, the same loop applies the change to this run only, and offers to save.
- **What's never stored,** saved or not:
  - raw MCP responses
  - addresses, phone numbers or payment data
  - other people's personal items
- **Order history:** stored only if the user asks for it, e.g. to avoid re-fetching. That's the choice ME made for `data/orders.jsonl` in this prototype.
- **No membership concept:** "before moving in / after moving out" is just a not-home date range with an open end. It lives in the same saved ruleset, or is answered fresh each run.

## 15. Personal items are never named: an allowlist, with personal as the default

**Decided (2026-09-27).**

**Problem:** a "personal items" list in the rules spells out sensitive purchases, and would ship in presets or saved rulesets.

**Where item names actually go:**

| Place | Sees item names? | Notes |
|---|---|---|
| The model (during fetch) | **yes, unavoidable** | MCP order details pass through the model, same as addresses (privacy rule 4) |
| Claude Code session history | yes | the host keeps local transcripts of the session, including tool output. Shorten retention with the host's transcript-cleanup setting if wanted |
| `rules.json` / presets / saved ruleset | **no, after this change** | contains only shared-item words and generic treat words |
| chat / terminal summary | **no** for personal items | counts and amounts only, e.g. "21 unlisted items (₹…) defaulted to personal" |
| `*-shared.csv` | no | personal rows excluded |
| private CSV, `orders.jsonl` | yes | local only; see the optional redaction below |

**Design:**
1. **Rules list what's shared** (veg, pantry, dairy, cleaning…) using precise patterns, e.g. "mint leaves", not "mint", which would also match a mouthwash.
2. **A few generic guard rules** (sweets, ice cream, snacks, cold drinks) exist only because their names overlap with dairy/veg words ("Dairy **Milk** Silk", "ice **cream**"). Guards use generic words only.
3. **Catch-all:** anything else is `unlisted`, which means personal. Sensitive items are never named anywhere in config.
4. **Safe failure direction:** if a genuinely shared item is missed, it defaults to the *buyer* paying. Others are never over-charged. The summary shows the unlisted count and total so the buyer can check privately.

**Tested on the prototype flat's 6 months of data:** removing every sensitive personal rule changed **₹0** of the split once three loose shared patterns were tightened ("oil", "mint", "mango").

**Optional extras** (cheap, not built yet):
- **Hashed personal preferences.** If a user's own "that's mine" preferences are themselves sensitive, the saved ruleset stores `sha256(salt + normalized item name)` instead of the name. The salt stays in the user's local config.
- **Redact unlisted items at rest.** `orders.jsonl` and the private CSV store only `unlisted item ₹amount` (plus a hash) for items no rule matched. The trade-off: a future rule can't reclassify them by name.

## 16. Review: questions in chat, rules that learn, privacy by default

**Decided (2026-09-27):** editing CSVs is too complicated. Review happens through **short click-to-answer questions**, and the answers update the ruleset. CSVs are **view-only**, so users can check every item and share and feel confident.

### 16a. How questions are asked
- **Grouped:** one question per *category or product*, never per row. "Buttermilk (6 purchases, ₹400): who shares it?"
- **Few:** at most about 5 per run, biggest money first. Anything unanswered keeps its default (personal), so the buyer pays and nobody else is over-charged.
- **Suggested answer preselected** (from the preset or similar past answers), so pressing Enter is usually right.
- **Answers map straight to rule actions:**
  - `Shared by whoever's home` → shared bucket, the default presence rule
  - `Shared by everyone, even if away` → shared bucket with `always`
  - `Only mine` → personal
  - `Only some of us → pick` → a group bucket
- **Scope follow-up, only when ambiguous:** "Just this order, or every time you buy it?"
- **Lists go inside the question, or in their own message.** A list written just before the question box can be hidden by the box (seen in testing, 27 Sep). When there are more than about 6 items, show the list, end the turn, and ask next turn.
- **Impact is shown before saving:** rows affected, and each person's total before → after. Then "Save to my rules?" This is the dry run of the engine (`apply_review.py`).

### 16b. What gets asked (the review queue)
| Trigger | Question | Names shown? |
|---|---|---|
| item no rule matched, but it looks shared (the name hits a shared-category word, only partly) | "Is X shared?" | yes (candidate shared item) |
| review flags (different address, refund, high-value shared) | "The 12 Jun order went to a different address. Split it, or yours?" | shared rows only |
| new product in an already-known category | none; the rule covers it | n/a |
| unlisted items defaulted to personal | **one consent question:** "12 items (₹3,500) defaulted to you. Look through them?" `[No, they're mine ✓] [Yes, show them]` | only if the user says yes |
| away dates | "Was anyone away this period?" | n/a |

### 16c. Self-improvement, in two loops
1. **Personal loop (automatic, local):** every saved answer becomes a rule or exception in the user's ruleset, with a date and a `note`. Next run, the question doesn't come back. Question count falls quickly: our house went from about 9 open categories to 0 over the first review.
2. **Universal loop (opt-in, anonymized):** when an answer is a *generic shared-item fact* ("buttermilk → kitchen, whoever's home"), the skill offers: "Suggest this as a default for everyone using the roommates-india preset?"
   - **Exported:** only the pattern word, the category and the policy.
   - **Never exported:** amounts, dates, names, short-names, order IDs, or anything personal. Personal items are never named in rules to begin with (§15).
   - **Destination:** a suggestions file the maintainer reviews before merging into the preset. Nothing is sent anywhere automatically.

### 16d. Privacy guarantees in the review loop
- Personal items are never named in questions unless the user opts in to see them for that run.
- Personal decisions are stored as salted hashes; shared decisions by readable name, which keeps them auditable.
- Impact summaries count personal changes without naming them.
- The model saw item names at fetch time (unavoidable). The loop just never repeats them or stores them in readable form.

### 16e. Seeing and changing your preferences
- **`/split-zepto prefs`** shows the saved ruleset in plain language (`show_prefs.py`):
  - people and not-home dates
  - how each kind of item is split (whoever's home vs even if away)
  - your decisions: shared ones by name, one-off exceptions as a count, confirmed-personal items as a count
- **Hidden items stay hidden unless you ask.** "Show my hidden items" matches the hashed keys against the user's *local* order history and lists the names in their own terminal. Nothing is written, and the names aren't needed anywhere else.
- **Changing works through the same questions:** "What do you want to change?"
  - `[Who shares a kind of item]` → pick a category → the same options as review
  - `[One item]` → name it → shared/mine/some of us, just this order or always
  - `[Away dates]` / `[People]` → add, edit or remove
  - `[Undo a decision]` → pick from the list above
  - Every change shows its impact first (dry run), then "Save?".
- **Automatic save points:** the first run offers to save (§14), and after that every review round ends with "Save to my rules?" per answer. Choosing "just this run" applies the answer to that run's files only, and the next rebuild from saved rules drops it.

## Open questions

1. ~~Who runs it~~ **Decided:** everyone runs it on their own orders (§11).
2. ~~Settlement~~ **Out of scope:** split calculation only (§5).
3. ~~Sources~~ **Decided:** Zepto only for now.
4. Where split files go: **recommended** option A (WhatsApp + fingerprint line). Needs ME's confirmation.
5. Shared file default: **item detail** (current) or **summary only** with detail on request?
