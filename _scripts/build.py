#!/usr/bin/env python3
"""Build the static data the check-UI loads.

Merges data/normalized.json + data/translations.json (cache, optional) into
public/data/programs.js (window global — works on file://, no server),
programs.json, and feed.xml (RSS 2.0). Pure.

Run: python3 _scripts/build.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter

from pages import make_pages, CAT_LABEL, REG_EN, STAGE_EN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://start.seoulcrushing.com"

_HANGUL = re.compile(r"[가-힣]")


def is_publishable(r):
    """A program ships only if its English is present and Korean-free — 'held'
    (untranslated / failed-translation) records are EXCLUDED from the payload,
    never rendered in Korean. This is the build-time gate behind the fail-safe."""
    te, se = r.get("title_en") or "", r.get("summary_en") or ""
    return bool(te) and not _HANGUL.search(te) and not _HANGUL.search(se)


def data_hash(programs):
    """Stable hash of published content (volatile build metadata excluded) so
    `generated` only advances when the data actually changes — makes
    commit-if-changed real (no daily no-op commits / CF redeploys)."""
    fields = ("id", "title_en", "summary_en", "target_en", "exclusions_en",
              "close_date", "open_date", "category", "region", "age_min", "age_max",
              "apply_url", "detail_url", "nationality_flag", "foreigner_relevance", "org_type")
    snap = [{k: p.get(k) for k in fields} for p in sorted(programs, key=lambda x: x.get("id", ""))]
    return hashlib.sha1(json.dumps(snap, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


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


def make_sitemap(programs, public_dir, site_url):
    """Emit public/sitemap.xml — home + each per-program clean URL (no .html;
    Cloudflare serves /start/<id> canonically)."""
    locs = [f"{site_url}/"] + [f"{site_url}/start/{p['id']}" for p in programs if p.get("id")]
    body = "\n".join(f"  <url><loc>{loc}</loc></url>" for loc in locs)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}\n</urlset>\n")
    with open(os.path.join(public_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)


def main():
    norm = json.load(open(os.path.join(ROOT, "data", "normalized.json"), encoding="utf-8"))
    tpath = os.path.join(ROOT, "data", "translations.json")
    trans = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {}
    opath = os.path.join(ROOT, "data", "org_types.json")
    orgtypes = json.load(open(opath, encoding="utf-8")) if os.path.exists(opath) else {}
    ovpath = os.path.join(ROOT, "data", "overrides.json")
    overrides = json.load(open(ovpath, encoding="utf-8")) if os.path.exists(ovpath) else {}
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
        ov = overrides.get(r["id"])
        if ov:
            r.update(ov)  # manual corrections (data/overrides.json) win over heuristic + translation

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

    # Build-time exclusion: only publishable (English, Korean-free) records ship.
    # Held records stay in normalized.json but never reach the public payload.
    publishable = [r for r in norm if is_publishable(r)]
    held = [r["id"] for r in norm if not is_publishable(r)]
    if held:
        print(f"⚠️  {len(held)} HELD (untranslated/Korean) — excluded from payload: {held[:8]}")

    facets = {
        "category": [k for k, _ in Counter(r["category"] for r in publishable).most_common()],
        "region": sorted({r["region"] for r in publishable if r["region"]}),
        "stage": sorted({s for r in publishable for s in r["business_stage"]}),
    }
    out = os.path.join(ROOT, "public", "data")
    os.makedirs(out, exist_ok=True)

    # Deterministic `generated`: reuse the prior timestamp when data is unchanged.
    dhash = data_hash(publishable)
    generated = dt.datetime.now().astimezone().isoformat(timespec="seconds")  # offset-aware (watchdog parses TZ)
    prior = os.path.join(out, "programs.js")
    if os.path.exists(prior):
        try:
            s = open(prior, encoding="utf-8").read()
            old = json.loads(s[s.index("=") + 1:].rstrip().rstrip(";"))
            if old.get("meta", {}).get("data_hash") == dhash:
                generated = old.get("generated", generated)
        except Exception:
            pass

    payload = {
        "generated": generated,
        "count": len(publishable),
        "meta": {"active_count": len(norm), "published_count": len(publishable), "data_hash": dhash},
        "facets": facets,
        "programs": publishable,
    }
    with open(os.path.join(out, "programs.js"), "w", encoding="utf-8") as f:
        f.write("window.KPN_DATA = " + json.dumps(payload, ensure_ascii=False) + ";")
    make_rss(publishable, out)
    npages = make_pages(publishable, os.path.join(ROOT, "public"), SITE_URL)
    make_sitemap(publishable, os.path.join(ROOT, "public"), SITE_URL)

    print(f"built: {len(norm)} active -> {len(publishable)} published ({len(held)} held) · pages {npages}")
    print(f"generated={generated} · data_hash={dhash}")


if __name__ == "__main__":
    main()
