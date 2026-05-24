#!/usr/bin/env bash
# refresh.sh — run the fail-safe refresh pipeline on demand.
#
# Fail-closed: any step's non-zero exit aborts BEFORE the commit, so the
# last-good deploy stays live. Pass --force to override a SOFT anomaly hold.
#
# Translation note: untranslated NEW programs are HELD (excluded from the build,
# never shown in Korean). To include them, a Claude Code session translates the
# missing content_hashes into a delta JSON, then runs validate_delta + enrich
# --merge (see step 3 below). The scheduled CC routine does this inline; a manual
# run publishes the already-translated set and reports what was held.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f REFRESH_FROZEN ]; then
  echo "REFRESH_FROZEN present — refresh paused. Remove the file to resume."
  exit 0
fi

echo "1/6 fetch  (aborts on API hiccup / sub-floor count)"
python3 _scripts/fetch_kstartup.py
RAW=$(ls -t data/raw/kstartup_active_*.json | head -1)

echo "2/6 normalize --input $RAW"
python3 _scripts/normalize.py --input "$RAW"

echo "3/6 translation status  (untranslated => HELD, excluded from the build)"
python3 _scripts/enrich.py || true
echo "    include held: CC translates -> delta.json, then"
echo "    python3 _scripts/validate_delta.py delta.json delta.clean.json && python3 _scripts/enrich.py --merge delta.clean.json"

echo "4/6 build  (excludes held; deterministic generated)"
python3 _scripts/build.py

echo "5/6 validate  (HARD + SOFT gates; fail-closed)"
python3 _scripts/validate_build.py "$@"

echo "6/6 commit-if-changed + push"
if git diff --quiet -- public/ data/translations.json data/overrides.json; then
  echo "    no changes — nothing to publish"
else
  git add public/ data/translations.json data/overrides.json
  git commit -q -m "data: refresh $(date +%F)"
  git push -q origin main && echo "    pushed -> Cloudflare auto-deploys"
fi
echo "✅ refresh complete"
