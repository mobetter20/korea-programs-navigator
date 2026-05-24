#!/usr/bin/env python3
"""Scheduled (launchd) refresh runner — pure Python, no bash wrapper.

launchd can't exec a bash script on a Documents-path (TCC), so the LaunchAgent
invokes python3 on THIS file directly. It runs the DETERMINISTIC fail-safe
pipeline:

    fetch -> normalize --input -> build -> validate_build -> commit-if-changed -> push

There is NO translation step here — translation needs a Claude Code session
(no paid AI API; see FAILSAFE.md). New programs without cached English are HELD
by build.py (excluded from the payload, never shown in Korean), so the live feed
stays correct between translation top-ups; closed programs still drop out daily.

Fail-closed: any step's non-zero exit aborts BEFORE the commit, leaving the
last-good commit live. Honors a REFRESH_FROZEN file at the repo root. Logs to
data/refresh.log (gitignored).

    python3 _scripts/scheduled_refresh.py [--dry-run]
"""
from __future__ import annotations

import datetime as dt
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LOG = os.path.join(ROOT, "data", "refresh.log")
DRY = "--dry-run" in sys.argv
TRACKED = ["public/", "data/fixtures/sample_record.json"]  # reverted on abort/dry-run


def log(msg: str) -> None:
    line = f"{dt.datetime.now().astimezone().isoformat(timespec='seconds')}  {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(args: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout or "").strip()
    if out:
        log(out.splitlines()[-1])
    if r.returncode != 0 and (r.stderr or "").strip():
        log(f"!! exit {r.returncode}: {r.stderr.strip()[:400]}")
    return r


def revert() -> None:
    subprocess.run(["git", "checkout", "--"] + TRACKED, cwd=ROOT,
                   capture_output=True, text=True)


def main() -> int:
    if os.path.exists(os.path.join(ROOT, "REFRESH_FROZEN")):
        log("REFRESH_FROZEN present — skipping refresh.")
        return 0
    log(f"=== refresh start{' (dry-run)' if DRY else ''} ===")

    if run([PY, "_scripts/fetch_kstartup.py"]).returncode != 0:
        log("ABORT: fetch failed — last-good untouched.")
        return 1
    raws = sorted(glob.glob(os.path.join(ROOT, "data", "raw", "kstartup_active_*.json")))
    if not raws:
        log("ABORT: no raw file after fetch.")
        return 1

    if run([PY, "_scripts/normalize.py", "--input", raws[-1]]).returncode != 0:
        log("ABORT: normalize failed."); revert(); return 1

    if run([PY, "_scripts/build.py"]).returncode != 0:
        log("ABORT: build failed — reverting."); revert(); return 1

    v = run([PY, "_scripts/validate_build.py"])
    if v.returncode != 0:
        log(f"ABORT: validate_build exit {v.returncode} — reverting; last-good stays live.")
        revert(); return v.returncode

    changed = subprocess.run(
        ["git", "diff", "--quiet", "--", "public/", "data/translations.json", "data/overrides.json"],
        cwd=ROOT).returncode != 0
    if not changed:
        log("no changes — nothing to publish."); log("=== refresh done ==="); return 0
    if DRY:
        log("[dry-run] would commit + push; reverting working tree.")
        revert(); log("=== refresh done (dry-run) ==="); return 0

    run(["git", "add", "public/", "data/translations.json", "data/overrides.json"])
    run(["git", "commit", "-q", "-m", f"data: refresh {dt.date.today().isoformat()}"])
    if run(["git", "push", "-q", "origin", "main"]).returncode != 0:
        log("WARN: push failed (commit is local + safe; retries next run). Check git creds in keychain.")
    else:
        log("pushed -> CF deploys once the GitHub webhook is reconnected.")
    log("=== refresh done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
