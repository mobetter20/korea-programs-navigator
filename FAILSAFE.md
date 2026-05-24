# FAILSAFE.md — the refresh pipeline & its guarantees

How Korea Programs Navigator stays fresh **without** ever publishing broken, empty,
untranslated, or unsafe content to the live site. Read this before changing
anything under `_scripts/` or the deploy wiring.

## The one principle

The live site changes **only** when a git commit lands on `main` and Cloudflare
Pages redeploys. So **the commit is the single fail-closed gate**: every step
validates *before* the commit, and if anything fails the pipeline aborts **before
committing** — leaving the last-good commit live. Nothing bad publishes because
nothing bad gets committed.

This only works because the generated artifacts (`public/data/`, `public/start/`)
are **git-tracked**. If they were gitignored, "rollback to last-good" and "keep
serving the previous deploy" would be fiction — there'd be nothing committed to
fall back to. `validate_build.py` asserts they're tracked on every run.

## Pipeline

```
fetch_kstartup.py     → data/raw/kstartup_active_<date>.json   (atomic: .tmp → rename; aborts if < FLOOR active)
normalize.py --input  → data/normalized.json                   (pure; abs_url http(s) allowlist; strip_html)
[CC translates deltas] → delta.json                            (Claude Code — the no-paid-API step)
validate_delta.py     → filtered delta                         (rejects empty/Korean/refusal → those stay HELD)
enrich.py --merge     → data/translations.json                 (content_hash-keyed cache)
build.py              → public/data/programs.js, feed.xml, public/start/*.html, public/sitemap.xml
validate_build.py     → HARD + SOFT gates                      (fail-closed: non-zero exit = abort, no commit)
commit-if-changed → push → Cloudflare auto-deploys public/
```

`./refresh.sh` runs all the shell steps on demand. The bracketed **translation**
step needs Claude Code (Haiku) — see *Running it*.

## The gates (two tiers)

The tiers are how "never publish bad" (safety) and "never get stuck" (liveness)
stop fighting: **HARD** gates govern *content* and never auto-release; **SOFT**
gates are *heuristics* that lean toward publishing.

| Gate | Tier | Behavior on failure |
|---|---|---|
| Artifacts git-tracked | HARD | abort — rollback would be a no-op otherwise |
| Every published program is English (no Korean/empty) | HARD | abort — proves build-time exclusion worked |
| `apply_url`/`detail_url` are http(s) only | HARD | abort — no `javascript:`/`data:` in an href |
| start-page count == `published_count`; sitemap == published + home | HARD | abort |
| **Held** = untranslated/failed-translation | (build) | **excluded** from payload, never shown in Korean |
| Sub-floor active count, or unexplained mass drop | SOFT | **hold + alert**; `--force` to override |
| Programs gone because `close_date` expired | SOFT | **expected — never holds** |
| Active-count spike | SOFT | logged, published anyway |
| Cold-start (no prior commit) | SOFT | seed + publish |

**`generated` is content-derived** — it only advances when the published data
actually changes (`build.py` reuses the prior timestamp if the content hash
matches). So a no-data-change refresh produces a byte-identical `programs.js` →
commit-if-changed skips → no needless CF redeploy.

## Running it

**Manual, on demand:**
```sh
./refresh.sh            # fetch → normalize → build → validate → commit-if-changed → push
./refresh.sh --force    # override a SOFT anomaly hold (after you've checked it's legit)
```
New programs whose English isn't cached yet are **held** (excluded, not shown in
Korean). To include them, run the **translation step** — in a Claude Code session:

1. `python3 _scripts/enrich.py` → lists the missing `content_hash`es + Korean source.
2. Translate them to warm, plain English (match the tone already in
   `data/translations.json`), write `delta.json` keyed by `content_hash`.
3. `python3 _scripts/validate_delta.py delta.json delta.clean.json`
4. `python3 _scripts/enrich.py --merge delta.clean.json`
5. `./refresh.sh` (build now includes them).

**Scheduled (autonomous) — INSTALLED, frozen:** a local launchd job runs the
deterministic pipeline daily at 06:00 KST — `com.ajin.korea-programs-navigator-refresh`
→ `_scripts/scheduled_refresh.py` (pure Python; launchd can't exec bash on a
Documents path). It does fetch → normalize → build → validate → commit-if-changed →
push, reading the key from local `.env`. It does **not** translate — new programs are
held (above) until a top-up; closed programs still drop daily. Missed days are low-harm
(D-day is client-side). **It is FROZEN** by a `REFRESH_FROZEN` file at the repo root.

To activate:
1. Reconnect the Cloudflare GitHub App (auto-deploy webhook) — else pushes don't publish.
2. `rm REFRESH_FROZEN`
3. Watch the first run — `tail -f data/refresh.log` — and confirm `git push` works from
   launchd (keychain creds may need a first-time unlock).

For fully-autonomous translation (no held lag), add a Claude Code translate step to the
runner — a `claude -p` call between normalize and build (deferred; held-behavior keeps
the feed correct meanwhile, per the no-paid-AI rule).

## Watchdog (independent)

`.github/workflows/watchdog.yml` runs on GitHub Actions every 6h — independent of
the refresh machine, because "the routine silently stopped" can't be detected by
the routine itself. It curls the live `programs.js`, and if `generated` is older
than 3 days (or unreachable) opens/updates a **`Navigator data health`** issue;
it closes the issue on recovery. Uses the built-in `GITHUB_TOKEN`, no secrets.
*(Note: `generated` = last data **change**; gov programs post often, so >3 days
stale in practice means the routine stopped. A genuinely quiet stretch is a
benign false-positive — check and close.)*

## Recover & freeze

- **Rollback:** `git revert <bad-sha> && git push` → CF redeploys last-good. Or
  the Cloudflare Pages dashboard → "Rollback to this deployment" (instant, no git).
- **Freeze:** create a `REFRESH_FROZEN` file at the repo root — `refresh.sh` exits
  immediately. Remove it to resume. (Owner-set/cleared only; the routine never
  writes it.)

## Owner activation checklist

- [ ] Scheduled CC routine created (prompt above) + `DATA_GO_KR_SERVICE_KEY` wired + push creds.
- [ ] GitHub Actions enabled for the repo + workflow permissions allow `issues: write` (for the watchdog).
- [ ] First supervised run: `./refresh.sh`, confirm it commits + the live site updates.
