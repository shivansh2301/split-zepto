# rules.json: the user's settings

It starts from `presets/roommates-india.json`, and every field can be edited.

```json
{
  "you": "ME",
  "buckets": {
    "grocery":   {"members": ["ME", "AK", "PS", "RJ"], "label": "Kitchen"},
    "household": {"members": ["ME", "AK", "PS", "RJ"], "label": "House"},
    "personal":  {"members": ["ME"], "label": "Personal"},
    "review":    {"members": null, "label": "Needs a decision"}
  },
  "denies":   {"PS": ["meat_seafood", "meat_masala"], "RJ": ["@grocery"]},
  "absences": {"PS": [["2026-06-05", "2026-06-25"]], "RJ": [[null, "2026-03-31"]]},
  "review_flags": {"home_pincode": "000000", "flag_other_pincode": true, "high_value_shared_rupees": 500, "flag_refunds": true},
  "rules": [ {"category": "pantry", "split": "grocery", "always": true, "pattern": "atta|rice|…"}, … ],
  "overrides": {"by_name": {}, "by_category": {}, "by_order_item": {}},
  "last_run_to": "2026-09-26"
}
```

| Field | Meaning |
|---|---|
| `buckets` | The pools. `grocery` is shown as **Kitchen**, `household` as **House**. Members are everyone who takes part in that pool |
| `denies` | Opt-outs. A category name, or `@pool` for the whole pool. Deny wins over everything else |
| `absences` | Inclusive IST date ranges when someone wasn't home. Covers trips, not having moved in yet, and having moved out |
| `rules` | Regexes checked **in order**; the first match wins. `split` is a bucket name. `"always": true` means everyone in the pool pays, even if away; use it only for long-lasting staples. Without it, only whoever was home pays |
| `overrides` | Decisions from reviews. `by_order_item[order_code][name or hash]` is a one-off; `by_name` means every purchase. Personal decisions are stored under `h:<hash>` keys by `apply_review.py`. Never write names for them yourself |
| `review_flags` | Which rows get a `review_flag` in the CSVs. Flags never change the split |

## Editing rules
- **Shared kinds of item:**
  - **Add or extend** a rule's `pattern` with precise words: "mint leaves", not "mint"; "mustard oil", not "oil".
  - **Word boundaries:** use `\b` around short words.
- **Personal items need no rule.** Anything unmatched falls through to `unlisted`, which is personal.
- **Guard rules** (split `personal`) exist only for generic treat words that overlap with shared words, e.g. "Dairy **Milk**" chocolate. Put them **above** the shared rules they overlap with.
- **After any edit,** rebuild and show each person's total before → after.
