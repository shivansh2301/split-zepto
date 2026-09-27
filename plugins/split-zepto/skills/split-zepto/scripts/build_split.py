#!/usr/bin/env python3
"""Build per-item Zepto cost-split CSVs and a summary from normalized order data.

Input:  data/orders.jsonl (one order per line, amounts in paise) + rules.json
Output: zepto_orders.csv  - every item, private to you (includes personal items)
        zepto_shared.csv  - shared items only, safe to send to the people you split with
        terminal summary. No network access.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
HERE = Path(__file__).resolve().parent


def home_dir(explicit=None):
    """Where the user's data lives: --home, else $SPLIT_ZEPTO_HOME, else ~/split-zepto. Never inside the skill folder."""
    return Path(explicit or os.environ.get("SPLIT_ZEPTO_HOME") or Path.home() / "split-zepto").expanduser()

COLUMNS = ["review_flag", "order_id", "order_date", "status", "item_name", "brand", "category",
           "quantity", "unit_price", "line_total", "order_delivery_fee",
           "order_discount", "order_total", "split", "split_among", "your_share"]


def rupees(paise):
    return "" if paise is None else f"{paise / 100:.2f}"


def placed_at(order):
    """Order time in IST; falls back to the UUIDv7 timestamp when 'placed' is missing."""
    if order.get("placed"):
        dt = datetime.fromisoformat(order["placed"].replace("Z", "+00:00"))
    else:
        ms = int(order["id"].replace("-", "")[:12], 16)
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.astimezone(IST)


def items_of(order):
    for it in order["items"]:
        if isinstance(it, dict):
            yield (it["name"], it.get("brand", ""), it["qty"], it.get("unit_price"),
                   it.get("line_total"), it.get("refund", 0))
        else:
            yield tuple(it)


def name_key(name, salt):
    """Unreadable key for an item name, so personal decisions can be saved without naming the item."""
    norm = " ".join(name.lower().split())
    return "h:" + hashlib.sha256((salt + norm).encode()).hexdigest()[:16]


class Classifier:
    def __init__(self, rules):
        self.salt = rules.get("privacy_salt", "")
        self.rules = [(r["category"], r["split"], not r.get("always", False), re.compile(r["pattern"], re.I))
                      for r in rules["rules"]]
        ov = rules.get("overrides", {})
        self.by_name = ov.get("by_name", {})
        self.by_order_item = ov.get("by_order_item", {})
        self.by_category = ov.get("by_category", {})

    def classify(self, name, unit_price, line_total, refund, order_code=None):
        """Returns (category, bucket, by_presence)."""
        name = name.strip()
        if unit_price == 0 and line_total == 0 and not refund:
            category, split, presence = "freebie", "personal", False
        else:
            category, split, presence = "uncategorized", "review", False
            for cat, spl, pres, rx in self.rules:
                if rx.search(name):
                    category, split, presence = cat, spl, pres
                    break
        split = self.by_category.get(category, split)
        hkey = name_key(name, self.salt)
        per_order = self.by_order_item.get(order_code, {})
        decided = self.by_name.get(name) or self.by_name.get(hkey) or per_order.get(name) or per_order.get(hkey)
        split = self.by_name.get(name, self.by_name.get(hkey, split))
        split = per_order.get(name, per_order.get(hkey, split))
        if decided and category == "unlisted":
            category = "confirmed_personal" if split == "personal" else "decided"
        return category, split, presence


class Presence:
    def __init__(self, absences):
        self.away = {person: [(date.fromisoformat(a) if a else date.min, date.fromisoformat(b) if b else date.max)
                              for a, b in ranges]
                     for person, ranges in absences.items() if not person.startswith("_")}

    def present(self, person, day):
        return not any(a <= day <= b for a, b in self.away.get(person, []))


def allocate(amount, weights):
    """Split an integer amount across weights proportionally; remainders go to the largest."""
    total = sum(weights)
    if not amount or not total:
        return [0] * len(weights)
    parts = [amount * w // total for w in weights]
    parts[max(range(len(weights)), key=lambda i: weights[i])] += amount - sum(parts)
    return parts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", help="data folder (default: $SPLIT_ZEPTO_HOME or ~/split-zepto)")
    ap.add_argument("--orders", type=Path)
    ap.add_argument("--rules", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--shared-out", type=Path)
    ap.add_argument("--review-out", type=Path)
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD (IST, inclusive)")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD (IST, inclusive)")
    args = ap.parse_args()
    home = home_dir(args.home)
    args.orders = args.orders or home / "data" / "orders.jsonl"
    args.rules = args.rules or home / "rules.json"
    args.out = args.out or home / "zepto_orders.csv"
    args.shared_out = args.shared_out or home / "zepto_shared.csv"
    args.review_out = args.review_out or home / "zepto_review.csv"

    rules = json.loads(args.rules.read_text())
    denies = {p: set(v) for p, v in rules.get("denies", {}).items() if not p.startswith("_")}
    buckets = rules["buckets"]
    you = rules.get("you", "ME")
    clf = Classifier(rules)
    presence = Presence(rules.get("absences", {}))
    people = []
    for b in buckets.values():
        for m in b.get("members") or []:
            if m not in people:
                people.append(m)

    orders = [json.loads(line) for line in args.orders.read_text().splitlines() if line.strip()]
    seen, unique = set(), []
    for o in orders:
        if o["id"] not in seen:
            seen.add(o["id"])
            unique.append(o)
    orders = sorted(unique, key=placed_at)

    d_from = date.fromisoformat(args.date_from) if args.date_from else None
    d_to = date.fromisoformat(args.date_to) if args.date_to else None
    orders = [o for o in orders
              if (not d_from or placed_at(o).date() >= d_from)
              and (not d_to or placed_at(o).date() <= d_to)]

    rf_cfg = rules.get("review_flags", {})
    home_pin = rf_cfg.get("home_pincode")
    high_value = int(rf_cfg.get("high_value_shared_rupees", 0) * 100)

    def flags_for(order, split, cost, refund):
        out = []
        pin = order.get("pincode")
        if home_pin and order["status"] == "DELIVERED":
            if pin and pin != home_pin and rf_cfg.get("flag_other_pincode", True):
                out.append("delivered to a different address")
            elif not pin and rf_cfg.get("flag_unknown_pincode", False):
                out.append("delivery pincode unknown")
        if high_value and split not in ("personal", "review") and cost >= high_value:
            out.append("high-value shared item")
        if refund and rf_cfg.get("flag_refunds", True):
            out.append("refunded")
        if split == "review":
            out.append("needs a split decision")
        return "; ".join(out)

    rows, shared_rows, review_rows, warnings = [], [], [], []
    bucket_totals = defaultdict(int)                 # bucket -> paise
    owes = defaultdict(lambda: defaultdict(float))   # person -> bucket -> paise
    review_items = defaultdict(lambda: [0, 0])       # (name, category) -> [count, paise]

    for o in orders:
        delivered = o["status"] == "DELIVERED"
        day = placed_at(o).date()
        its = list(items_of(o))
        nets = [(lt or 0) - (rf or 0) for _, _, _, _, lt, rf in its]
        fee_parts = allocate(o.get("fees") or 0, nets)
        disc_parts = allocate(o.get("order_discount") or 0, nets)

        if delivered:
            expected = (o["grand_total"] or 0) - (o.get("refund") or 0)
            got = sum(nets) + (o.get("fees") or 0) - (o.get("order_discount") or 0)
            if got != expected:
                warnings.append(f"{o['code']}: items+fees-discount = {rupees(got)} but order total-refund = {rupees(expected)}")

        for (name, brand, qty, unit, lt, rf), net, fee, disc in zip(its, nets, fee_parts, disc_parts):
            category, split, by_presence = clf.classify(name, unit, lt, rf, o["code"])
            cost = net + fee - disc
            members = buckets[split].get("members") or []
            if by_presence:
                members = [m for m in members if m == you or presence.present(m, day)]
            # Deny wins: a person can opt out of a category, or of a whole pool ("@grocery").
            members = [m for m in members if not ({category, "@" + split} & denies.get(m, set()))]
            share = ""
            flag = flags_for(o, split, cost, rf)
            if delivered and members:
                bucket_totals[split] += cost
                for m in members:
                    owes[m][split] += cost / len(members)
                share = rupees(round(cost / len(members))) if you in members else "0.00"
                if split != "personal":
                    shared_rows.append({
                        "review_flag": flag,
                        "order_date": day.isoformat(), "order_id": o["code"],
                        "item_name": name.strip(), "brand": brand, "category": category,
                        "bucket": split, "quantity": qty, "amount": rupees(cost),
                        "split_among": "+".join(members),
                        **{p: rupees(round(cost / len(members))) if p in members else "" for p in people},
                    })
            if delivered:
                attention = bool(flag) or category == "unlisted"
                review_rows.append({
                    "_attention": attention,
                    "check": "CHECK" if attention else "",
                    "review_flag": flag, "order_date": day.isoformat(), "order_id": o["code"],
                    "item_name": name.strip(), "category": category, "split": split,
                    "split_among": "+".join(members), "amount": rupees(cost),
                    **{p: rupees(round(cost / len(members))) if members and p in members else "" for p in people},
                })
            if delivered and not members:
                r = review_items[(name.strip(), category)]
                r[0] += 1
                r[1] += cost
            rows.append({
                "review_flag": flag if delivered else "",
                "order_id": o["code"],
                "order_date": day.isoformat(),
                "status": o["status"],
                "item_name": name.strip(),
                "brand": brand,
                "category": category,
                "quantity": qty,
                "unit_price": rupees(None if lt is None else round(lt / qty)) if qty else "",
                "line_total": rupees(None if lt is None else net),
                "order_delivery_fee": rupees(o.get("fees") or 0),
                "order_discount": rupees(o.get("order_discount") or 0),
                "order_total": rupees(o.get("grand_total")),
                "split": split if delivered else f"{split} (not delivered)",
                "split_among": "+".join(members) if delivered else "",
                "your_share": share,
            })

    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    review_cols = ["check", "review_flag", "order_date", "order_id", "item_name",
                   "category", "split", "split_among", "amount"] + people
    review_rows.sort(key=lambda r: (not r["_attention"], r["order_date"]), reverse=False)
    with args.review_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=review_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(review_rows)

    shared_cols = ["review_flag", "order_date", "order_id", "item_name", "brand", "category", "bucket",
                   "quantity", "amount", "split_among"] + people
    with args.shared_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=shared_cols)
        w.writeheader()
        w.writerows(shared_rows)
        blank = {c: "" for c in shared_cols}
        w.writerow(blank)
        total_row = dict(blank, item_name="TOTAL (shared items)",
                         amount=rupees(sum(v for b, v in bucket_totals.items() if b != "personal")))
        total_row.update({p: rupees(round(sum(v for b, v in owes[p].items() if b != "personal")))
                          for p in people})
        w.writerow(total_row)

    # ---- summary ----
    def r(x):
        return f"₹{x / 100:,.2f}"

    delivered_orders = sum(1 for o in orders if o["status"] == "DELIVERED")
    first = placed_at(orders[0]).date() if orders else None
    last = placed_at(orders[-1]).date() if orders else None
    print(f"Wrote {len(rows)} rows to {args.out.name} (private), {len(shared_rows)} to {args.shared_out.name} (shareable), "
          f"{len(review_rows)} to {args.review_out.name} (private, view-only; CHECK rows first)")
    print(f"Orders: {len(orders)} ({delivered_orders} delivered) from {first} to {last}\n")
    for b, cfg in buckets.items():
        if cfg.get("members"):
            print(f"  {cfg.get('label', b):<18} {r(bucket_totals[b]):>12}   among {', '.join(cfg['members'])}")
    rv_total = sum(v[1] for v in review_items.values())
    print(f"  {'Review (pending)':<18} {r(rv_total):>12}   <- not in any total yet\n")

    bucket_names = [b for b, c in buckets.items() if c.get("members")]
    print("  " + f"{'Person':<22}" + "".join(f"{b:>12}" for b in bucket_names) + f"{'TOTAL':>13}")
    for p in people:
        vals = [owes[p][b] for b in bucket_names]
        tag = " (you)" if p == you else " owes you"
        print("  " + f"{p + tag:<22}" + "".join(f"{r(v):>12}" for v in vals) + f"{r(sum(vals)):>13}")
    print("  (assumes you paid every order)")
    absences = {k: v for k, v in rules.get("absences", {}).items() if not k.startswith("_")}
    if absences:
        print("  Away (only always-split pantry items charged): " +
              "; ".join(f"{p} {a or '…'}→{b or '…'}" for p, rs in absences.items() for a, b in rs))

    unlisted = [r for r in rows if r["category"] == "unlisted" and r["status"] == "DELIVERED"]
    if unlisted:
        amt = sum(float(r["line_total"] or 0) for r in unlisted)
        print(f"\n  {len(unlisted)} unlisted items (₹{amt:,.2f}) defaulted to personal. Names are only in the private CSV "
              "(filter category = unlisted) if you want to check none should be shared.")

    flagged = [r for r in rows if r["review_flag"]]
    if flagged:
        print(f"\nFlagged for a look ({len(flagged)} rows; filter the review_flag column):")
        by_flag = defaultdict(list)
        for row in flagged:
            for f in row["review_flag"].split("; "):
                by_flag[f].append(row)
        for f, lst in by_flag.items():
            print(f"  [{f}] {len(lst)} rows")
            for row in lst[:8]:
                label = "(personal item — see private CSV)" if row["split"] == "personal" else row["item_name"][:50]
                print(f"      {row['order_date']} {row['order_id']} {row['split']:<10} {label}")
            if len(lst) > 8:
                print(f"      … {len(lst) - 8} more")

    if review_items:
        print("\nReview items (add a rule or override in rules.json):")
        by_cat = defaultdict(list)
        for (name, cat), (cnt, amt) in review_items.items():
            by_cat[cat].append((amt, cnt, name))
        for cat in sorted(by_cat, key=lambda c: -sum(a for a, _, _ in by_cat[c])):
            lst = sorted(by_cat[cat], reverse=True)
            print(f"  [{cat}] {r(sum(a for a, _, _ in lst))}")
            for amt, cnt, name in lst:
                print(f"      {r(amt):>10}  ×{cnt:<3} {name}")

    if warnings:
        print("\nTotal mismatches (check these orders):", file=sys.stderr)
        for wmsg in warnings:
            print("  " + wmsg, file=sys.stderr)


if __name__ == "__main__":
    main()
