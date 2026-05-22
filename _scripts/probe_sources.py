#!/usr/bin/env python3
"""Ingestion spike — Korea Programs Navigator.

Probes the two MVP data sources (K-Startup + Bizinfo) and reports whether the
data premise holds: can we pull foreign-resident-relevant startup/business
programs with parseable eligibility + contact fields?

Both APIs require a FREE auth key (auto-approved). Set them in .env or env:
  BIZINFO_CRTFC_KEY        — bizinfo.go.kr  (활용정보 > 정책정보 개방)
  DATA_GO_KR_SERVICE_KEY   — data.go.kr     (dataset 15125364, 활용신청)

Run:  python3 _scripts/probe_sources.py
(stdlib only — no pip install needed.)
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

# Foreigner / visa-eligibility signal terms scanned in the returned text.
FOREIGN_TERMS = ["외국인", "다문화", "결혼이민", "영주", "이민", "귀화", "국적"]
NATIONAL_ONLY_TERMS = ["내국인", "대한민국 국민", "국민에 한", "한국 국적"]
CONTACT_INDICATORS = ["연락", "전화", "담당", "문의", "tel", "cnpl", "phone", "email", "이메일"]


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "kpn-spike/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _scan(items):
    """Estimate foreigner-eligibility + contact signal across returned items."""
    blob = " ".join(str(it) for it in items)
    foreign = sum(blob.count(t) for t in FOREIGN_TERMS)
    natl = sum(blob.count(t) for t in NATIONAL_ONLY_TERMS)
    contact_hits = sum(
        1 for it in items if any(ci in str(it).lower() for ci in CONTACT_INDICATORS)
    )
    print(f"  foreigner-relevant term hits (외국인/다문화/결혼이민/영주/…): {foreign}")
    print(f"  national-only term hits (내국인/국민에 한/…):              {natl}")
    print(f"  items with a contact-like field/value:                  {contact_hits}/{len(items)}")


def probe_bizinfo(key):
    print("\n=== Bizinfo (기업마당) ===")
    if not key:
        print("  SKIP — set BIZINFO_CRTFC_KEY (free, bizinfo.go.kr → 활용정보 > 정책정보 개방)")
        return
    params = {"crtfcKey": key, "dataType": "json", "searchCnt": "20"}
    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do?" + urllib.parse.urlencode(params)
    try:
        status, body = _get(url)
    except Exception as e:  # noqa: BLE001 — spike: report any failure plainly
        print(f"  request failed: {e}")
        return
    print(f"  HTTP {status}, {len(body)}b")
    try:
        data = json.loads(body)
    except Exception:
        print("  (not JSON — first 400 bytes:)")
        print("  " + body[:400].decode("utf-8", "replace"))
        return
    items = data.get("jsonArray") or data.get("items") or []
    print(f"  items returned: {len(items)}")
    if items:
        print("  sample item keys: " + ", ".join(sorted(items[0].keys())))
        _scan(items)
    else:
        print("  top-level keys: " + ", ".join(map(str, data.keys())))
        print("  raw snippet: " + body[:300].decode("utf-8", "replace"))


def probe_kstartup(key):
    print("\n=== K-Startup (창업진흥원) ===")
    if not key:
        print("  SKIP — set DATA_GO_KR_SERVICE_KEY (free, data.go.kr dataset 15125364, 활용신청)")
        return
    params = {"serviceKey": key, "page": "1", "perPage": "20", "returnType": "json"}
    url = (
        "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01?"
        + urllib.parse.urlencode(params)
    )
    try:
        status, body = _get(url)
    except Exception as e:  # noqa: BLE001
        print(f"  request failed: {e}")
        return
    print(f"  HTTP {status}, {len(body)}b")
    try:
        data = json.loads(body)
    except Exception:
        print("  (not JSON — first 400 bytes:)")
        print("  " + body[:400].decode("utf-8", "replace"))
        return
    items = data.get("data") or data.get("response", {}).get("body", {}).get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    print(f"  items returned: {len(items)}")
    if items:
        print("  sample item keys: " + ", ".join(sorted(items[0].keys())))
        _scan(items)
    else:
        print("  top-level keys: " + ", ".join(map(str, data.keys())))
        print("  raw snippet: " + body[:300].decode("utf-8", "replace"))


def main():
    # Minimal .env loader (no dependency on python-dotenv).
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    print("Korea Programs Navigator — ingestion spike")
    print("(reports whether the data premise holds; needs 2 free keys)")
    probe_bizinfo(os.environ.get("BIZINFO_CRTFC_KEY"))
    probe_kstartup(os.environ.get("DATA_GO_KR_SERVICE_KEY"))
    print("\nDone. Premise holds if both returned items carrying 지원대상/문의처-type fields.")


if __name__ == "__main__":
    main()
