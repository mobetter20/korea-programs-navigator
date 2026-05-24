#!/usr/bin/env python3
"""Translation sanity gate — filter a Claude-Code-produced translation delta
BEFORE it reaches the cache. Rejects entries that would publish bad/Korean/empty
English. The agent writes the delta; THIS script (not the agent) decides what
passes — so a translation lapse is contained, never self-graded through.

Rejected entries are simply omitted (the program stays "held" until a good
translation arrives, and build.py excludes held records from the payload).

Usage: python3 _scripts/validate_delta.py IN.json OUT.json
"""
from __future__ import annotations

import json
import re
import sys

HANGUL = re.compile(r"[가-힣]")
REFUSAL = re.compile(r"(i can'?t|i cannot|i'm sorry|cannot translate|as an ai|unable to translate)", re.I)


def check(entry: dict) -> tuple[bool, str]:
    te = (entry.get("title_en") or "").strip()
    if not te:
        return False, "empty title_en"
    if HANGUL.search(te):
        return False, "Korean in title_en"
    if REFUSAL.search(te):
        return False, "refusal marker in title_en"
    if len(te) > 300:
        return False, "title_en implausibly long"
    se = entry.get("summary_en") or ""
    if HANGUL.search(se):
        return False, "Korean in summary_en"
    if REFUSAL.search(se):
        return False, "refusal marker in summary_en"
    return True, ""


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_delta.py IN.json OUT.json")
    incoming = json.load(open(sys.argv[1], encoding="utf-8"))
    clean, rejects = {}, []
    for k, v in incoming.items():
        ok, why = check(v)
        (clean.__setitem__(k, v) if ok else rejects.append((k, why)))
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=1)
    print(f"validate_delta: {len(clean)} pass, {len(rejects)} rejected (held)")
    for k, why in rejects[:20]:
        print(f"  REJECT {k}: {why}")
    # Non-zero only if EVERY entry was rejected — signals a broken translation run.
    if incoming and not clean:
        raise SystemExit("ABORT: all delta entries rejected — translation run looks broken")


if __name__ == "__main__":
    main()
