# DESIGN — v1 ingestion + schema

Status: **plan-critic-hardened + live-measured (2026-05-23).** Implements North-Star v4 (README).

## v1 scope (locked)

- **Source:** K-Startup only. Bizinfo → v1.1.
- **Active filter:** `rcrt_prgs_yn=="Y"` **AND** (`pbanc_rcpt_end_dt` empty OR `>= today`). The flag alone is stale ~8% (27/323 on 2026-05-23). Server ignores the filter → fetch pulls all (~29 pages), dedupes, filters client-side.
- **Measured 2026-05-23:** **296 active** of 28,758 total; `pbanc_sn` 100% unique (28,758/28,758) → reliable dedupe key; 0 empty-close (rolling) in current active set.
- **Spine:** structured matching (stage · age · region · category) over the *eligible* pool; visa = input + flag.

## Schema (one record / program)

| Field | Type | Source / parse |
|---|---|---|
| `id` / `source` | str | `ks-<pbanc_sn>` / `"kstartup"` |
| `title_ko`/`_en`, `summary_ko`/`_en` | str | `biz_pbanc_nm` / `pbanc_ctnt` (strip HTML) → LLM translate |
| `category` | enum(11) | `supt_biz_clsfc`, **HTML-unescaped** |
| `business_stage[]` | enum[] | split `biz_enyy` on `,` → tokens |
| `age_min`/`age_max` | int\|null | parse `biz_trgt_age` (see rule) |
| `region` | str | `supt_regin` |
| `target_ko`, `exclusions_ko` | str\|null | `aply_trgt`+`aply_trgt_ctnt`, `aply_excl_trgt_ctnt` |
| `nationality_flag` | enum | heuristic, anchored (see rule) |
| `confidence` | enum | `explicit` / `inferred` (silent) |
| `foreigner_relevance` | enum | `general_eligible`(default) / `inbound_global` / `outbound_na` / `foreigner_targeted` |
| `open_date`/`close_date`/`is_active` | date/bool | `pbanc_rcpt_bgng_dt`/`_end_dt`, filter above |
| `contact_phone` | str\|null | `prch_cnpl_no` |
| `detail_url`/`apply_url` | str | `detl_pg_url` / fallback chain (see rule) |
| `agency` | str | `pbanc_ntrp_nm` / `sprv_inst` |
| `last_refreshed`/`content_hash` | ts/str | pipeline meta |

**Parse rules (from plan-critic + live data):**
- **`category`** — 11 real values, HTML-unescape (`기술개발(R&amp;D)`→`기술개발(R&D)`): 사업화 · 멘토링ㆍ컨설팅ㆍ교육 · 시설ㆍ공간ㆍ보육 · 행사ㆍ네트워크 · 창업교육 · 판로ㆍ해외진출 · 글로벌 · 기술개발(R&D) · 인력 · 융자ㆍ보증 · 정책자금.
- **`business_stage[]`** — split `biz_enyy` on `,` → subset of {예비창업자, 1년미만, 2년미만, 3년미만, 5년미만, 7년미만, 10년미만} (24 combos live).
- **`age_min/max`** — split `biz_trgt_age` on `,`; min(lower)/max(upper) across bands; **the all-bands case (만20미만 + …이상~…이하 + …이상) = NO age limit (null/null), never (20,39).** 5 formats live.
- **`apply_url`** — fallback: `aply_mthd_onli_rcpt_istc` → `biz_aply_url` → `detl_pg_url` (online-receipt often null).
- **`nationality_flag`** — anchored phrases ONLY: `내국인에 한`/`대한민국 국민에 한`/`국민에 한(?:하|함)` → `barred`; `외국인`/`재외국민` in target → `explicit_foreign`; else `silent`. **Never bare `국민`** (avoids "전국민 대상" = open-to-all). Scan `aply_trgt`+`aply_trgt_ctnt`+`aply_excl_trgt_ctnt`.

## Pipeline (daily)

1. **fetch_kstartup.py** — pull all, dedupe `pbanc_sn`, filter active. ✅ built.
2. **normalize.py** — raw active → schema via parse rules. Pure (no net/LLM); tested against `data/fixtures/sample_record.json`.
3. **enrich.py** — **cache manager only, NO API.** Field-level `--merge` of Claude-Code-produced translations into `data/translations.json` (keyed by `content_hash` = sha1 of `title_ko`+`summary_ko`). Reports missing/stale. **Translation + inbound/outbound judgment run via Claude Code Haiku subagents** (no paid AI API — owner rule `feedback_no_paid_ai_api`), not an API key.
   - fields cached: `title_en`, `summary_en`, `target_en` (eligibility), `exclusions_en` (faithful, never condensed), `foreigner_relevance`.
   - `foreigner_relevance`: inbound/outbound judgment ONLY for **글로벌 + 판로ㆍ해외진출**; else `general_eligible`. `outbound_na` down-ranks, never excludes.
4. **build.py** — merge `translations.json` + `org_types.json` into records; emit `programs.js`/`.json`, `feed.xml`, per-program `start/<id>.html`, `stats.html`. Drift guards warn on unknown category/region/stage enums or untranslated records.
5. **refresh** — a **scheduled Claude Code routine** (NOT a plain GH Action — the translation step bars an API-calling Action under no-paid-API): fetch → normalize → CC translates new/changed deltas → enrich --merge → build → commit. Deferred until remote exists.

## Dedupe decision (made explicit)

Key = `pbanc_sn` (verified unique). **v1 = show each announcement** — do *not* collapse `intg_pbanc_yn=Y` children under `intg_pbanc_biz_nm`. Rationale: comprehensive (hide nothing), simpler, and the matching filter controls clutter. Revisit if a parent spams near-duplicate children. (API's own `id` 1..N is page-relative — ignored.)

## Trust guards (failure-mode: untrustworthy data)

- `is_active` = flag **AND** date — no stale-Y false "open."
- `nationality_flag` never hard-excludes; `silent` → "no bar stated — verify"; always keep `*_ko` originals.
- structured fields parsed, never LLM-guessed; LLM only translates + judges inbound/outbound.
- `data/fixtures/sample_record.json` (redacted) anchors parser regression tests.
