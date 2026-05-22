#!/usr/bin/env python3
"""Build the static data the check-UI loads.

Merges data/normalized.json + data/translations.json (cache, optional) into
public/data/programs.js (window global — works on file://, no server) and
programs.json. Pure.

Run: python3 _scripts/build.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    norm = json.load(open(os.path.join(ROOT, "data", "normalized.json"), encoding="utf-8"))
    tpath = os.path.join(ROOT, "data", "translations.json")
    trans = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {}
    for r in norm:
        t = trans.get(r["content_hash"])
        if t:
            r["title_en"] = t.get("title_en") or r["title_en"]
            r["summary_en"] = t.get("summary_en") or r["summary_en"]
            if t.get("foreigner_relevance"):
                r["foreigner_relevance"] = t["foreigner_relevance"]

    facets = {
        "category": [k for k, _ in Counter(r["category"] for r in norm).most_common()],
        "region": sorted({r["region"] for r in norm if r["region"]}),
        "stage": sorted({s for r in norm for s in r["business_stage"]}),
    }
    payload = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "count": len(norm), "facets": facets, "programs": norm,
    }
    out = os.path.join(ROOT, "public", "data")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "programs.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "programs.js"), "w", encoding="utf-8") as f:
        f.write("window.KPN_DATA = " + json.dumps(payload, ensure_ascii=False) + ";")

    print(f"built {len(norm)} programs -> public/data/  (translated: {sum(1 for r in norm if r['title_en'])}/{len(norm)})")
    print("facets:", {k: len(v) for k, v in facets.items()})


if __name__ == "__main__":
    main()
