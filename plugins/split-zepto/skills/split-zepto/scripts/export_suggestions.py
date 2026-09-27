#!/usr/bin/env python3
"""Export an anonymous contribution from your local rules.json.

Keeps only generic, shareable knowledge: category patterns for SHARED items and how
they're split (pool, whoever's home vs always). Drops everything about you:
short-names, pools' members, away dates, one-off exceptions, hidden personal decisions,
the privacy salt, notes, and any rule that makes something personal.

The output (contribution.json) is safe to paste into a GitHub issue or pull request.
Read it before you share it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_split import home_dir  # noqa: E402
PERSON = re.compile(r"\b[A-Z]{2,3}\b")        # short-names like AK, PS
DATEISH = re.compile(r"\d{4}-\d{2}-\d{2}")
# Generic "treat" guards are shared too: without them, "Dairy Milk Silk" would match dairy.
GUARDS = {"ice_cream", "sweets", "biscuits", "snacks", "cold_drinks"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", help="data folder (default: $SPLIT_ZEPTO_HOME or ~/split-zepto)")
    ap.add_argument("--rules", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    home = home_dir(args.home)
    args.rules = args.rules or home / "rules.json"
    args.out = args.out or home / "contribution.json"
    rules = json.loads(args.rules.read_text())

    pools = {b: ("kitchen" if b in ("grocery", "meat") else "house" if b == "household" else b)
             for b in rules["buckets"]}
    kept, dropped = [], 0
    for r in rules["rules"]:
        if r["category"] in GUARDS:
            kept.append({"category": r["category"], "pool": None, "participation": "buyer",
                         "pattern": r["pattern"], "role": "guard (generic treat words that overlap dairy/veg names)"})
            continue
        if r["split"] in ("personal", "review") or r["category"] == "unlisted":
            dropped += 1
            continue
        if PERSON.search(r["pattern"]) or DATEISH.search(r["pattern"]):
            dropped += 1
            continue
        kept.append({
            "category": r["category"],
            "pool": pools.get(r["split"], r["split"]),
            "participation": "always" if r.get("always") else "whoever_home",
            "pattern": r["pattern"],
        })

    out = {
        "_about": "Anonymous category suggestions for the roommates-india preset. Contains no people, dates, amounts or personal items.",
        "preset": "roommates-india",
        "rules": kept,
    }
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.out.name}: {len(kept)} shared-item rules kept, {dropped} personal/private rules left out.")
    print("Open it and check it yourself before sharing.")


if __name__ == "__main__":
    main()
