#!/usr/bin/env python3
"""Fetch K-Startup active programs + measure the pool (DESIGN.md step 1).

The API ignores rcrt_prgs_yn server-side, so we pull all announcements,
dedupe by pbanc_sn, and filter to *active* client-side:
    active = rcrt_prgs_yn=="Y" AND (no close_date OR close_date >= today)
(plan-critic: the flag alone is stale ~4% of the time.)

Reports the numbers needed to lock the schema: true active count, the real
supt_biz_clsfc enum (HTML-unescaped), and biz_trgt_age / biz_enyy format variety.

Saves active subset  -> data/raw/kstartup_active_<date>.json   (gitignored)
Saves redacted sample -> data/fixtures/sample_record.json       (committed anchor)

Needs DATA_GO_KR_SERVICE_KEY (.env).  Run: python3 _scripts/fetch_kstartup.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import urllib.parse
import urllib.request
from collections import Counter

BASE = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
PER_PAGE = 1000
MAX_PAGES = 40
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def fetch_page(key, page):
    qs = urllib.parse.urlencode(
        {"serviceKey": key, "page": page, "perPage": PER_PAGE, "returnType": "json"}
    )
    req = urllib.request.Request(f"{BASE}?{qs}", headers={"User-Agent": "kpn-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def is_active(rec, today):
    if rec.get("rcrt_prgs_yn") != "Y":
        return False
    end = (rec.get("pbanc_rcpt_end_dt") or "").strip()
    return (not end) or (end >= today)  # empty close = rolling/상시 -> active


def main():
    load_env()
    key = os.environ.get("DATA_GO_KR_SERVICE_KEY")
    if not key:
        raise SystemExit("set DATA_GO_KR_SERVICE_KEY in .env")
    today = dt.date.today().strftime("%Y%m%d")

    seen, total = {}, 0
    for page in range(1, MAX_PAGES + 1):
        rows = fetch_page(key, page).get("data", [])
        if not rows:
            break
        total += len(rows)
        for rec in rows:
            seen[rec.get("pbanc_sn")] = rec  # dedupe by pbanc_sn
        if len(rows) < PER_PAGE:
            break

    recs = list(seen.values())
    active = [r for r in recs if is_active(r, today)]
    flag_y = [r for r in recs if r.get("rcrt_prgs_yn") == "Y"]

    print(f"fetched rows: {total} | unique pbanc_sn: {len(recs)} (dup rows: {total - len(recs)})")
    print(f"flag=Y: {len(flag_y)} | truly active (flag AND date): {len(active)} "
          f"| stale-Y past close: {len(flag_y) - len(active)}")
    print("--- supt_biz_clsfc enum across ACTIVE (HTML-unescaped) ---")
    for k, v in Counter(html.unescape(r.get("supt_biz_clsfc", "")) for r in active).most_common():
        print(f"   {v:>4}  {k}")
    print(f"--- biz_trgt_age distinct formats (active): {len({r.get('biz_trgt_age','') for r in active})}")
    print(f"--- biz_enyy distinct formats (active): {len({r.get('biz_enyy','') for r in active})}")
    print(f"--- with empty close_date (rolling?): {sum(1 for r in active if not (r.get('pbanc_rcpt_end_dt') or '').strip())}")

    FLOOR = 20
    if len(active) < FLOOR:
        raise SystemExit(f"ABORT: only {len(active)} active (< floor {FLOOR}) — likely an API hiccup; "
                         "NOT overwriting the last-good raw. Re-run later.")
    os.makedirs(os.path.join(ROOT, "data", "raw"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "data", "fixtures"), exist_ok=True)
    final = os.path.join(ROOT, "data", "raw", f"kstartup_active_{today}.json")
    tmp = final + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(active, f, ensure_ascii=False, indent=1)
    os.replace(tmp, final)  # atomic promote: a partial/failed write never becomes the "latest" raw
    import glob as _glob  # prune old raws — keep the 7 most recent (gitignored; unbounded otherwise)
    for old in sorted(_glob.glob(os.path.join(ROOT, "data", "raw", "kstartup_active_*.json")))[:-7]:
        try:
            os.remove(old)
        except OSError:
            pass
    if active:
        fx = dict(active[0])
        fx["prch_cnpl_no"] = "REDACTED"
        with open(os.path.join(ROOT, "data", "fixtures", "sample_record.json"), "w", encoding="utf-8") as f:
            json.dump(fx, f, ensure_ascii=False, indent=2)
    print(f"saved {len(active)} active records -> data/raw/kstartup_active_{today}.json")


if __name__ == "__main__":
    main()
