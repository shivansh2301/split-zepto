# Contributing

The split gets better as more flats teach it which items are **shared** and how. The most useful contributions are new or better **category patterns** for everyday shared items (vegetables, pantry, dairy, cleaning, …) and fixes for items that were put in the wrong category.

**The one rule:** contributions describe *products*, never *people*. Nobody needs to know who you live with, what you personally buy, or how much you spend.

## Never include
- names, short-names (AK, PS…), addresses, pincodes, phone numbers or emails
- order IDs, dates, amounts, receipts or screenshots of the Zepto app
- anything you marked as **yours / personal**, or anything that defaulted to personal
- your `rules.json`, `orders.jsonl` or any CSV. These are ignored by git on purpose.

---

## Option 1: export from your own rules (easiest, about 1 minute)

If you've been using the skill, your saved rules already hold what you've taught it. You can also just ask your assistant to *"export my split suggestions"*.

```bash
python3 plugins/split-zepto/skills/split-zepto/scripts/export_suggestions.py   # writes ~/split-zepto/contribution.json
```

- **Kept:** only generic shared-item patterns and how they're split, plus the generic "treat" guard words (sweets, ice cream, snacks, cold drinks). The guards stop names like *Dairy **Milk** Silk* from being counted as dairy.
- **Left out automatically:** short-names, pool members, away dates, one-off exceptions, hidden personal decisions, notes and every personal rule.
- **Next:**
  1. Open `contribution.json` and read it.
  2. If you're happy with it, paste it into a new GitHub issue titled **"Category suggestions"**.

## Option 2: ask an AI to write the contribution for you

Use this if you'd rather describe things in plain words, or you want help turning a mis-categorised item into a rule. Copy the prompt below into Claude (or any AI chat). Then paste either your `contribution.json` or a plain description of how your flat splits things.

```text
You are helping me contribute anonymously to an open-source Zepto expense-split tool.
It sorts grocery items into categories using regex patterns, and each category has:
- pool: "kitchen" (food), "house" (cleaning/home) or null (the buyer pays)
- participation: "whoever_home" (default) or "always" (long-lasting staples like rice, atta, oil, ghee, spices)
Anything that matches no pattern is treated as personal. So I only need to describe SHARED items,
plus generic "guard" words for treats whose names overlap with food words (e.g. "Dairy Milk" chocolate).

Here is what my flat does (my exported contribution.json, or my plain-words description):
<PASTE HERE>

Write a contribution with these strict rules:
1. Output ONLY JSON: {"preset": "roommates-india", "rules": [{"category", "pool", "participation", "pattern", "why"}]}
2. Describe products, never people. Remove any names, initials, dates, amounts, order IDs, addresses,
   pincodes and anything that sounds like one person's private purchase (personal care, health,
   intimate, tobacco, medicines, clothing). If in doubt, leave it out.
3. Patterns: lowercase regex, precise words ("mint leaves", not "mint"; "mustard oil", not "oil"),
   use \b word boundaries for short words, and "|" between alternatives.
4. Guard rules (pool null) may only use generic treat words: chocolate, ice cream, cookie, chips, soft drink…
5. For each rule, add a one-line "why" (e.g. "makhana is a shared snack in many flats").
6. After the JSON, list anything you removed for privacy, in one line, without repeating it.
```

**Before posting:** read the AI's output yourself, check it contains no personal details, then open an issue titled **"Category suggestions"** with the JSON.

## Option 3: report a wrong category
If a *shared, everyday* product lands in the wrong place, open an issue with:
- **the product name** as Zepto shows it (only if it's a common shared item such as "Aashirvaad Select Atta 5 kg")
- **what it was treated as**, and what it should be (category + pool)

If the wrong match was a *personal* item that ended up shared, don't name it. Describe it generically ("a personal-care product matched the `oil` pattern"), and we'll tighten the shared pattern instead.

---

## Pattern guidelines (for pull requests)
- **Rules describe shared items.** Personal items need no rule, because they default to the buyer. Never add a rule that names a sensitive personal product.
- **First match wins.** Put guards and specific rules above broad ones.
- **Be precise.** A loose word causes false matches ("mint" caught a mouthwash; "oil" caught a hair-spa mask).
- **Participation:** `always` only for long-lasting staples; everything else is `whoever_home`.
- **Category names:** lowercase with underscores (`fruit_veg`, `pantry`, `cleaning`).

## How contributions are checked
Maintainers merge suggestions into `plugins/split-zepto/skills/split-zepto/presets/roommates-india.json` only after replaying them against anonymized test data. A new rule must not move any item that was already classified correctly. Contributions that include personal details are closed and the content removed.
