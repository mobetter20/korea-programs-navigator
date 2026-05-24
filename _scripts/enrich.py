#!/usr/bin/env python3
"""Enrich cache manager for Korea Programs Navigator.

Manages data/translations.json (keyed by content_hash).
Translation is performed by the Claude Code session — no paid AI API.

Usage:
  python3 _scripts/enrich.py              # report missing/stale translations
  python3 _scripts/enrich.py --merge FILE # merge a CC-produced translations JSON

Pipeline: fetch -> normalize -> [CC session translates delta] -> enrich --merge -> build
"""
from __future__ import annotations

import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORM = os.path.join(ROOT, "data", "normalized.json")
TRANS = os.path.join(ROOT, "data", "translations.json")


def load_trans() -> dict:
    return json.load(open(TRANS, encoding="utf-8")) if os.path.exists(TRANS) else {}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--merge", metavar="FILE",
                   help="merge CC-produced translations JSON into cache")
    args = p.parse_args()

    norm = json.load(open(NORM, encoding="utf-8"))
    trans = load_trans()

    if args.merge:
        incoming = json.load(open(args.merge, encoding="utf-8"))
        fields = 0
        for k, v in incoming.items():
            entry = trans.setdefault(k, {})
            for fk, fv in v.items():
                if fv and entry.get(fk) != fv:  # field-level: never clobber with empty
                    entry[fk] = fv
                    fields += 1
        with open(TRANS, "w", encoding="utf-8") as f:
            json.dump(trans, f, ensure_ascii=False, indent=1)
        print(f"merged {fields} field-updates into cache ({len(trans)} entries)")
        return

    # Report status
    missing = [r for r in norm
               if r["content_hash"] not in trans
               or not trans[r["content_hash"]].get("title_en")]
    print(f"cache: {len(trans)} entries  normalized: {len(norm)}  missing: {len(missing)}")
    if missing:
        print("needs translation (content_hash | category | title_ko):")
        for r in missing[:20]:
            print(f"  {r['content_hash']} | {r['category']} | {r['title_ko'][:60]}")
        if len(missing) > 20:
            print(f"  … and {len(missing) - 20} more")
    else:
        print("all records translated — ready for build.py")


if __name__ == "__main__":
    main()
