#!/usr/bin/env python3
"""Show the saved split preferences in plain language.

Personal decisions are stored as unreadable keys, so they're shown as a count only.
--reveal matches those keys against your *local* order history and lists the item
names in your terminal (nothing is written anywhere).
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_split import home_dir, items_of, name_key  # noqa: E402

LABELS = {
    "pantry": "rice, atta, dal, oil, ghee, pickle", "spices": "spices, masalas, salt",
    "nuts": "almonds, cashews", "meat_masala": "chicken masala", "fruit_veg": "vegetables & fruit",
    "dairy": "milk, curd, butter, cream", "eggs": "eggs", "bakery_fresh": "bread, pav, batter, parota",
    "paneer": "paneer", "buttermilk": "buttermilk", "cheese_processed": "cheese slices",
    "diet_coke": "Diet Coke", "instant_noodles": "instant noodles", "cleaning": "cleaning supplies",
    "home": "home items", "meat_seafood": "chicken, prawns, goat",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", help="data folder (default: $SPLIT_ZEPTO_HOME or ~/split-zepto)")
    ap.add_argument("--rules", type=Path)
    ap.add_argument("--orders", type=Path)
    ap.add_argument("--reveal", action="store_true", help="list hidden personal decisions by name (local only)")
    args = ap.parse_args()
    home = home_dir(args.home)
    args.rules = args.rules or home / "rules.json"
    args.orders = args.orders or home / "data" / "orders.jsonl"
    rules = json.loads(args.rules.read_text())
    buckets = rules["buckets"]

    print("PEOPLE")
    for b, cfg in buckets.items():
        if cfg.get("members") and b != "personal":
            print(f"  {cfg.get('label', b):<16} shared by {', '.join(cfg['members'])}")
    for p, what in ((k, v) for k, v in rules.get("denies", {}).items() if not k.startswith("_")):
        pretty = [("all of " + buckets[w[1:]].get("label", w[1:])) if w.startswith("@") else LABELS.get(w, w.replace("_", " ")) for w in what]
        print(f"  {p} denies: {', '.join(pretty)}")
    away = {k: v for k, v in rules.get("absences", {}).items() if not k.startswith("_")}
    for p, ranges in away.items():
        for a, b in ranges:
            print(f"  {p} not home {a or 'before'} → {b or 'now'}")

    print("\nHOW THINGS ARE SPLIT")
    groups = defaultdict(list)
    for r in rules["rules"]:
        if r["split"] in ("personal", "review"):
            continue
        how = "even if someone's away" if r.get("always") else "among whoever was home"
        groups[(r["split"], how)].append(LABELS.get(r["category"], r["category"].replace("_", " ")))
    for (bucket, how), cats in groups.items():
        print(f"  {buckets[bucket].get('label', bucket)}, {how}: {'; '.join(cats)}")
    print("  Everything else: yours (not named anywhere)")

    ov = rules.get("overrides", {})
    by_name = ov.get("by_name", {})
    by_order = ov.get("by_order_item", {})
    shared_named = {k: v for k, v in by_name.items() if not k.startswith("h:")}
    hidden = {k for k in by_name if k.startswith("h:")}
    one_offs = sum(len(v) for v in by_order.values())
    notes = [r["_note"] for r in rules["rules"] if r.get("_note") and r["category"] != "unlisted"]

    print("\nYOUR DECISIONS")
    for k, v in shared_named.items():
        print(f"  {k} → {v}")
    for n in notes:
        print(f"  rule: {n}")
    print(f"  {one_offs} one-off exceptions on specific orders")
    print(f"  {len(hidden)} items confirmed as yours (hidden" + ("" if args.reveal else "; run with --reveal to list them locally") + ")")

    if args.reveal and hidden:
        salt = rules.get("privacy_salt", "")
        names = set()
        for line in args.orders.read_text().splitlines():
            if line.strip():
                for it in items_of(json.loads(line)):
                    if name_key(it[0].strip(), salt) in hidden:
                        names.add(it[0].strip())
        for n in sorted(names):
            print(f"    - {n}")


if __name__ == "__main__":
    main()
