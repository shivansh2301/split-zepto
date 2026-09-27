#!/usr/bin/env python3
"""Build release zips for non-developer installs (attach them to a GitHub Release).

dist/split-zepto-skill.zip   → ChatGPT (Skills → Upload), Codex (~/.agents/skills), claude.ai skill upload
dist/split-zepto-plugin.zip  → claude.ai / Claude desktop (Customize → Plugins → Upload plugin)

Refuses to package if any personal data file is inside the plugin folder.
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "split-zepto"
SKILL = PLUGIN / "skills" / "split-zepto"
DIST = ROOT / "dist"
FORBIDDEN = re.compile(r"(^|/)(rules\.json|rules\.json\.bak|orders\.jsonl|contribution\.json|.*\.csv|data/)", re.I)


def files_under(base):
    return [p for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


def build(src, zip_path, arc_root):
    bad = [str(p.relative_to(src)) for p in files_under(src) if FORBIDDEN.search(str(p.relative_to(src)))]
    if bad:
        sys.exit(f"Refusing to package: personal data files found in {src}: {bad}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files_under(src):
            z.write(p, f"{arc_root}/{p.relative_to(src)}")
        z.write(ROOT / "LICENSE", f"{arc_root}/LICENSE")  # GPL: ship the license with every copy
    print(f"{zip_path.relative_to(ROOT)}: {len(files_under(src))} files")


if __name__ == "__main__":
    DIST.mkdir(exist_ok=True)
    build(SKILL, DIST / "split-zepto-skill.zip", "split-zepto")
    build(PLUGIN, DIST / "split-zepto-plugin.zip", "split-zepto")
