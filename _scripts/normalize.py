#!/usr/bin/env python3
"""Normalize raw K-Startup active records -> unified schema (DESIGN.md).

Pure: no network, no LLM. Reads the latest data/raw/kstartup_active_*.json,
writes data/normalized.json. English fields left blank (filled by enrich step).

Run: python3 _scripts/normalize.py
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import html
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CATS = {"글로벌", "판로ㆍ해외진출"}
# anchored phrases only — never bare 국민 (avoids "전국민 대상" = open-to-all)
BARRED_RE = re.compile(r"(내국인에\s*한|대한민국\s*국민에\s*한|국민에\s*한(?:하|함|정))")
FOREIGN_RE = re.compile(r"(외국인|재외국민)")


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def to_iso(yyyymmdd):
    s = (yyyymmdd or "").strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 and s.isdigit() else None


def parse_age(s):
    """Comma-aware. Returns (min, max); None = no bound. All-bands -> (None, None)."""
    if not s:
        return None, None
    lows, highs = [], []
    for seg in s.split(","):
        nums = [int(n) for n in re.findall(r"(\d+)\s*세", seg)]
        if not nums:
            continue
        if "~" in seg or ("이상" in seg and "이하" in seg):
            lows.append(min(nums)); highs.append(max(nums))
        elif "미만" in seg:
            lows.append(0); highs.append(min(nums) - 1)
        elif "이하" in seg:
            lows.append(0); highs.append(max(nums))
        elif "이상" in seg:
            lows.append(min(nums)); highs.append(200)
        else:
            lows.append(min(nums)); highs.append(max(nums))
    if not lows:
        return None, None
    lo, hi = min(lows), max(highs)
    return (None if lo <= 0 else lo), (None if hi >= 200 else hi)


def nationality(target, excl):
    blob = f"{target or ''} {excl or ''}"
    if BARRED_RE.search(blob):
        return "barred", "explicit"
    if FOREIGN_RE.search(target or ""):
        return "explicit_foreign", "explicit"
    return "silent", "inferred"


def normalize(rec):
    target = " ".join(filter(None, [rec.get("aply_trgt"), rec.get("aply_trgt_ctnt")]))
    excl = rec.get("aply_excl_trgt_ctnt")
    nat, conf = nationality(target, excl)
    cat = html.unescape(rec.get("supt_biz_clsfc") or "")
    amin, amax = parse_age(rec.get("biz_trgt_age"))
    title_ko = rec.get("biz_pbanc_nm") or ""
    summary_ko = strip_html(rec.get("pbanc_ctnt"))
    chash = hashlib.sha1(f"{title_ko}\x1f{summary_ko}".encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"ks-{rec.get('pbanc_sn')}",
        "source": "kstartup",
        "title_ko": title_ko, "title_en": "",
        "summary_ko": summary_ko, "summary_en": "",
        "category": cat,
        "business_stage": [t.strip() for t in (rec.get("biz_enyy") or "").split(",") if t.strip()],
        "age_min": amin, "age_max": amax,
        "region": rec.get("supt_regin") or "",
        "target_ko": target.strip(),
        "exclusions_ko": (excl or "").strip() or None,
        "nationality_flag": nat, "confidence": conf,
        "foreigner_relevance": "needs_judgment" if cat in GLOBAL_CATS else "general_eligible",
        "open_date": to_iso(rec.get("pbanc_rcpt_bgng_dt")),
        "close_date": to_iso(rec.get("pbanc_rcpt_end_dt")),
        "is_active": True,
        "contact_phone": rec.get("prch_cnpl_no"),
        "detail_url": rec.get("detl_pg_url"),
        "apply_url": rec.get("aply_mthd_onli_rcpt_istc") or rec.get("biz_aply_url") or rec.get("detl_pg_url"),
        "agency": rec.get("pbanc_ntrp_nm") or rec.get("sprv_inst") or "",
        "content_hash": chash,
    }


def main():
    raws = sorted(glob.glob(os.path.join(ROOT, "data", "raw", "kstartup_active_*.json")))
    if not raws:
        raise SystemExit("no data/raw/kstartup_active_*.json — run fetch_kstartup.py first")
    src = raws[-1]
    out = [normalize(r) for r in json.load(open(src, encoding="utf-8"))]
    with open(os.path.join(ROOT, "data", "normalized.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"normalized {len(out)} from {os.path.basename(src)}")
    print("nationality_flag:", dict(Counter(r["nationality_flag"] for r in out)))
    print("foreigner_relevance:", dict(Counter(r["foreigner_relevance"] for r in out)))
    print("no age limit:", sum(1 for r in out if r["age_min"] is None and r["age_max"] is None), "/", len(out))
    print("missing apply_url:", sum(1 for r in out if not r["apply_url"]))
    s = out[0]
    print("sample:", json.dumps({k: s[k] for k in ("id","title_ko","category","business_stage","age_min","age_max","region","nationality_flag","close_date")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
