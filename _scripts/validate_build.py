#!/usr/bin/env python3
"""Post-build gate — run after build.py, BEFORE commit. Fail-closed: a non-zero
exit aborts the refresh, so the last-good commit stays live.

HARD checks (never auto-released — a failure always blocks):
  * generated artifacts are git-tracked (else rollback / "last-good" is a no-op)
  * programs.js parses and is non-empty
  * every PUBLISHED program has English (no Korean, no empty title) — proves the
    build-time exclusion worked and nothing ships in Korean
  * apply_url / detail_url use only http(s) (no javascript:/data: in an href)
  * start-page count == published_count; sitemap == published + home

SOFT anomaly gate (heuristic — override with --force):
  * sub-floor active count, or an *unexplained* mass drop (programs gone without
    their close_date expiring), holds + alerts. Expiry is expected, never holds.
  * a spike is logged, never held. Cold-start (no prior commit) seeds + passes.

Usage: python3 _scripts/validate_build.py [--force]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
HANGUL = re.compile(r"[가-힣]")
FLOOR = 20
DROP_FRAC = 0.5  # an unexplained drop bigger than this (of prior active) holds


def _parse_js(text: str) -> dict:
    return json.loads(text[text.index("=") + 1:].rstrip().rstrip(";"))


def _prior_committed() -> dict | None:
    """Last committed programs.js (HEAD) — the last-good baseline for anomaly diff."""
    try:
        out = subprocess.check_output(
            ["git", "-C", ROOT, "show", "HEAD:public/data/programs.js"],
            text=True, stderr=subprocess.DEVNULL)
        return _parse_js(out)
    except Exception:
        return None


def main() -> None:
    force = "--force" in sys.argv
    errs: list[str] = []

    # HARD: artifacts tracked (rollback precondition)
    for path in ("public/data/programs.js", "public/data/feed.xml", "public/sitemap.xml"):
        try:
            subprocess.check_output(["git", "-C", ROOT, "ls-files", "--error-unmatch", path],
                                    stderr=subprocess.DEVNULL)
        except Exception:
            errs.append(f"{path} is NOT git-tracked — rollback/last-good would be a no-op")

    d = _parse_js(open(os.path.join(PUB, "data", "programs.js"), encoding="utf-8").read())
    progs = d.get("programs", [])
    pub = d.get("meta", {}).get("published_count", len(progs))
    act = d.get("meta", {}).get("active_count", len(progs))
    if not progs:
        errs.append("0 published programs")

    # HARD: every published program is English + has only http(s) URLs
    for p in progs:
        te, se = p.get("title_en") or "", p.get("summary_en") or ""
        if not te or HANGUL.search(te) or HANGUL.search(se):
            errs.append(f"{p.get('id')}: non-English/empty in payload (should have been held)")
        for u in (p.get("apply_url"), p.get("detail_url")):
            if u and u.split(":", 1)[0].lower() not in ("http", "https"):
                errs.append(f"{p.get('id')}: unsafe URL scheme -> {u!r}")

    # HARD: page + sitemap counts match published
    npages = len([f for f in os.listdir(os.path.join(PUB, "start")) if f.endswith(".html")])
    if npages != pub:
        errs.append(f"start-page count {npages} != published_count {pub}")
    nsm = open(os.path.join(PUB, "sitemap.xml"), encoding="utf-8").read().count("<url>")
    if nsm != pub + 1:
        errs.append(f"sitemap urls {nsm} != published+home {pub + 1}")

    if errs:
        print("❌ HARD gate FAILED — NOT safe to commit:")
        for e in errs[:40]:
            print("  -", e)
        raise SystemExit(1)

    # SOFT: anomaly vs last commit (expiry-aware)
    prior = _prior_committed()
    if prior is None:
        print(f"✅ HARD gate passed · cold-start (no prior commit) · published {pub}/{act}")
        return
    prior_act = prior.get("meta", {}).get("active_count", prior.get("count", 0))
    soft: list[str] = []
    if act < FLOOR:
        soft.append(f"active {act} < floor {FLOOR}")
    if prior_act and act < prior_act * (1 - DROP_FRAC):
        today = dt.date.today().isoformat()
        now_ids = {p.get("id") for p in progs}
        dropped = {p.get("id") for p in prior.get("programs", [])} - now_ids
        expired = {p.get("id") for p in prior.get("programs", [])
                   if (p.get("close_date") or "9999-99-99") < today}
        unexplained = dropped - expired
        if len(unexplained) > prior_act * DROP_FRAC:
            soft.append(f"unexplained drop: {len(unexplained)} programs gone without expiring "
                        f"(active {prior_act} -> {act})")
    if soft and not force:
        print("⚠️  SOFT anomaly gate HELD (investigate, or re-run with --force):")
        for s in soft:
            print("  -", s)
        raise SystemExit(2)
    if prior_act and act > prior_act * 3:
        print(f"ℹ️  spike: active {prior_act} -> {act} (published anyway; logged)")
    print(f"✅ all gates passed · published {pub}/{act} (prior active {prior_act})"
          + (" [FORCED past soft hold]" if force and soft else ""))


if __name__ == "__main__":
    main()
