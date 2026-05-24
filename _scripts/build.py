#!/usr/bin/env python3
"""Build the static data the check-UI loads.

Merges data/normalized.json + data/translations.json (cache, optional) into
public/data/programs.js (window global — works on file://, no server),
programs.json, and feed.xml (RSS 2.0). Pure.

Run: python3 _scripts/build.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import xml.etree.ElementTree as ET
from collections import Counter

from pages import make_pages, make_stats, CAT_LABEL, REG_EN, STAGE_EN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://korea-programs-navigator.local"


def make_rss(programs: list, out_dir: str) -> None:
    """Emit RSS 2.0 of programs sorted by open_date desc, max 60 items."""
    rss = ET.Element("rss", version="2.0")
    ch = ET.SubElement(rss, "channel")
    ET.SubElement(ch, "title").text = "Korea Programs Navigator — Active Programs"
    ET.SubElement(ch, "link").text = SITE_URL
    ET.SubElement(ch, "description").text = (
        "Korean government startup and business-support programs for foreign residents"
    )
    ET.SubElement(ch, "language").text = "en"

    items = sorted(
        (p for p in programs if p.get("open_date")),
        key=lambda p: p["open_date"],
        reverse=True,
    )[:60]

    for p in items:
        item = ET.SubElement(ch, "item")
        title = p.get("title_en") or p.get("title_ko", "")
        desc = p.get("summary_en") or p.get("summary_ko", "")
        link = p.get("apply_url") or p.get("detail_url") or SITE_URL
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "description").text = desc
        ET.SubElement(item, "guid", isPermaLink="false").text = p["id"]
        d = dt.date.fromisoformat(p["open_date"])
        pub = dt.datetime.combine(d, dt.time()).strftime("%a, %d %b %Y %H:%M:%S +0900")
        ET.SubElement(item, "pubDate").text = pub

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    path = os.path.join(out_dir, "feed.xml")
    with open(path, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)


def main():
    norm = json.load(open(os.path.join(ROOT, "data", "normalized.json"), encoding="utf-8"))
    tpath = os.path.join(ROOT, "data", "translations.json")
    trans = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {}
    opath = os.path.join(ROOT, "data", "org_types.json")
    orgtypes = json.load(open(opath, encoding="utf-8")) if os.path.exists(opath) else {}
    for r in norm:
        r["org_type"] = orgtypes.get(r.get("agency", ""), "Other")
        t = trans.get(r["content_hash"])
        if t:
            r["title_en"] = t.get("title_en") or r["title_en"]
            r["summary_en"] = t.get("summary_en") or r["summary_en"]
            if t.get("foreigner_relevance"):
                r["foreigner_relevance"] = t["foreigner_relevance"]
            if t.get("target_en"):
                r["target_en"] = t["target_en"]
            if t.get("exclusions_en"):
                r["exclusions_en"] = t["exclusions_en"]

    # Drift guards — surface anything that would render as raw Korean or untranslated.
    unknown_cat = sorted({r["category"] for r in norm if r["category"] and r["category"] not in CAT_LABEL})
    unknown_reg = sorted({r["region"] for r in norm if r["region"] and r["region"] not in REG_EN})
    unknown_stage = sorted({s for r in norm for s in r["business_stage"] if s not in STAGE_EN})
    untranslated = [r["id"] for r in norm if not r.get("title_en")]
    for label, items in [("categories (add to CAT_LABEL)", unknown_cat),
                         ("regions (add to REG_EN)", unknown_reg),
                         ("stages (add to STAGE_EN)", unknown_stage)]:
        if items:
            print(f"⚠️  DRIFT: unknown {label}: {items} — these render as raw Korean")
    if untranslated:
        print(f"⚠️  {len(untranslated)} programs UNTRANSLATED (would show Korean): {untranslated[:8]}")

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
    make_rss(norm, out)
    npages = make_pages(norm, os.path.join(ROOT, "public"))
    make_stats(norm, os.path.join(ROOT, "public"))

    print(f"built {len(norm)} programs -> public/data/  (translated: {sum(1 for r in norm if r['title_en'])}/{len(norm)})")
    print("facets:", {k: len(v) for k, v in facets.items()})
    print(f"rss: public/data/feed.xml")
    print(f"overview pages: public/start/ ({npages})")


if __name__ == "__main__":
    main()
