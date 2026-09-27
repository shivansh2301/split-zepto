#!/usr/bin/env python3
"""Engine behind the chat review: apply decisions to rules.json.

The skill asks the user questions, writes their answers as a small decisions CSV
(columns: order_id, item_name, decision, scope) and runs this script, dry run first.
Users are not expected to edit CSVs themselves.

Fill the `decision` column for any row you want to change:
    P / personal     G / grocery     H / household     M / meat     (or any bucket name in rules.json)
and optionally `scope`:
    blank or 1   -> just this purchase (one-off exception)
    all          -> every purchase of this item, now and in future runs

Default is a dry run: shows what would change and the new per-person totals, and writes nothing.
Run again with --apply to save the decisions into rules.json (a backup is kept) and rebuild.
Personal decisions are saved as unreadable keys, so rules.json never names personal items.
"""
import argparse
import csv
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_split import home_dir, name_key  # noqa: E402

ALIASES = {"p": "personal", "g": "grocery", "h": "household", "m": "meat"}


def totals(shared_csv):
    rows = list(csv.DictReader(open(shared_csv, encoding="utf-8")))
    total = next((r for r in rows if r["item_name"].startswith("TOTAL")), None)
    people = [c for c in rows[0].keys() if c not in (
        "review_flag", "order_date", "order_id", "item_name", "brand", "category",
        "bucket", "quantity", "amount", "split_among")] if rows else []
    return {p: float(total[p] or 0) for p in people} if total else {}


def run_build(rules_path, outdir, date_from, home):
    subprocess.run([sys.executable, str(HERE / "build_split.py"), "--home", str(home), "--rules", str(rules_path),
                    "--out", str(outdir / "o.csv"), "--shared-out", str(outdir / "s.csv"),
                    "--review-out", str(outdir / "r.csv")] + (["--from", date_from] if date_from else []),
                   check=True, capture_output=True)
    return outdir / "o.csv", outdir / "s.csv"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("review_csv", type=Path, help="decisions CSV: order_id,item_name,decision,scope")
    ap.add_argument("--home", help="data folder (default: $SPLIT_ZEPTO_HOME or ~/split-zepto)")
    ap.add_argument("--rules", type=Path)
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--apply", action="store_true", help="save decisions to rules.json and rebuild")
    args = ap.parse_args()
    home = home_dir(args.home)
    args.rules = args.rules or home / "rules.json"

    rules = json.loads(args.rules.read_text())
    buckets = [b for b in rules["buckets"] if b != "review"]
    rules.setdefault("privacy_salt", secrets.token_hex(8))
    salt = rules["privacy_salt"]
    ov = rules.setdefault("overrides", {})
    by_name = ov.setdefault("by_name", {})
    by_order = ov.setdefault("by_order_item", {})

    decisions, errors = [], []
    for i, row in enumerate(csv.DictReader(open(args.review_csv, encoding="utf-8-sig")), start=2):
        d = row.get("decision", "").strip().lower()
        if not d:
            continue
        bucket = ALIASES.get(d, d)
        scope = row.get("scope", "").strip().lower() or "1"
        if bucket not in buckets:
            errors.append(f"line {i}: unknown decision '{row['decision']}' (use P/G/H/M or one of {buckets})")
        elif scope not in ("1", "all", "*"):
            errors.append(f"line {i}: unknown scope '{row['scope']}' (use blank/1 or all)")
        else:
            decisions.append((row, bucket, "all" if scope in ("all", "*") else "1"))
    if errors:
        print("Fix these in the review sheet first:\n  " + "\n  ".join(errors))
        sys.exit(1)
    if not decisions:
        print("No decisions found. Fill the `decision` column (P/G/H/M) for rows to change.")
        return

    for row, bucket, scope in decisions:
        # Personal decisions are stored under an unreadable key; shared ones stay readable for auditing.
        key = name_key(row["item_name"], salt) if bucket == "personal" else row["item_name"]
        if scope == "all":
            by_name[key] = bucket
        else:
            by_order.setdefault(row["order_id"], {})[key] = bucket

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "rules.json").write_text(json.dumps(rules, indent=2, ensure_ascii=False) + "\n")
        (tmp / "before").mkdir()
        (tmp / "after").mkdir()
        o_before, s_before = run_build(args.rules, tmp / "before", args.date_from, home)
        o_after, s_after = run_build(tmp / "rules.json", tmp / "after", args.date_from, home)

        key = lambda r: (r["order_id"], r["item_name"])
        old = {key(r): r for r in csv.DictReader(open(o_before, encoding="utf-8")) if r["status"] == "DELIVERED"}
        changed = [(old[key(r)], r) for r in csv.DictReader(open(o_after, encoding="utf-8"))
                   if r["status"] == "DELIVERED" and old[key(r)]["split_among"] != r["split_among"]]
        tb, ta = totals(s_before), totals(s_after)

    print(f"{len(decisions)} decisions → {len(changed)} rows change:")
    hidden = 0
    for o, n in changed:
        if "personal" in (o["split"], n["split"]):
            hidden += 1
            continue
        print(f"  {n['order_date']} {n['order_id']}  {o['split_among']} → {n['split_among']}  {n['item_name'][:50]}")
    if hidden:
        print(f"  …and {hidden} rows moving to/from personal (names hidden; see your review sheet)")
    print("\nShared totals per person (before → after):")
    for p in ta:
        print(f"  {p:<6} ₹{tb.get(p, 0):>10,.2f} → ₹{ta[p]:>10,.2f}")

    if not args.apply:
        print("\nDry run. Nothing saved. Re-run with --apply to save these decisions.")
        return
    shutil.copy(args.rules, args.rules.with_suffix(".json.bak"))
    args.rules.write_text(json.dumps(rules, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, str(HERE / "build_split.py"), "--home", str(home), "--rules", str(args.rules)] + (["--from", args.date_from] if args.date_from else []), check=True)
    print(f"\nSaved to {args.rules.name} (backup: {args.rules.with_suffix('.json.bak').name}). Review sheet regenerated with decisions cleared.")


if __name__ == "__main__":
    main()
