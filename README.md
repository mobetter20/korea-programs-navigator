# Korea Programs Navigator

> **Working title.** Public name is a launch-time decision (see Open decisions). Don't pitch the visa filter — pitch the user's problem: *Korea's startup/business support, navigable, in English.*

English-language navigator that aggregates Korean government **startup & business-support** programs from open APIs and surfaces what a **foreign resident** can actually apply for. Comprehensive underneath, one scannable card per program on top. Visual/architecture sibling: [seoulcrushing.com](../seoulcrushing.com).

## Status — LIVE

**https://start.seoulcrushing.com** — v1 shipped 2026-05-24 (296 active K-Startup programs, English, privacy-first static). The **START** pillar of the Seoul Crushing house; public name shipped as **Start**.

- **Run / refresh the data:** `./refresh.sh` — the full pipeline, gates, translation step, scheduled-routine activation, rollback, and freeze are in **[FAILSAFE.md](./FAILSAFE.md)**.
- **Deploy:** own public repo → its own Cloudflare Pages project (auto-deploys on push to `main`) → custom domain `start.seoulcrushing.com`. No analytics, no third-party requests, self-hosted fonts.

## North-Star

Make Korea's startup- and business-support universe **navigable** for foreign residents who want to build something here — surfacing the programs they're **actually eligible for** (far more than they realize), **matched to their situation** (stage · age · region · sector), readable **in English**. Comprehensive underneath, ruthlessly simple on top: one program = one scannable card filtered to *you*, never a 28,000-row haystack. Honest about fit — shows what matches and how to verify it, flags the rare nationality bars — **never promising you qualify.**

**Drift signals:** (a) coverage gaps hollowing out "comprehensive"; (b) surface going layered as coverage grows — *matched/simple wins the top, comprehensive the back end*; (c) data that doesn't earn trust — stale, or LLM-guessed where a structured field exists; (d) implying eligibility certainty the data can't support; (e) drifting either way off-target — shrinking to a tiny "foreigner-only" ghetto, OR sliding to outbound / Korean-national / general-expat content; (f) runtime LLM, analytics, or tracking.

## Audience & scope (MVP)

- **Audience A — foreign-resident founders.** People on F-6 / F-5 / F-2 etc. who want to start or run a business in Korea. User-zero: project owner (F-6).
- **Domain: entrepreneurship / startup / business-support only.** Rides the two richest sources; broader civic aggregators deferred.
- **다문화 / 결혼이민 entrepreneur programs** are a *featured high-confidence sub-set* (explicit eligibility language → "wow discovery" candidate), not the product's headline.
- **Contact info** is captured and shown when present, but carries no weight — not the primary CTA. (Brief's "contact-as-primary-action" principle retired.)
- English only at launch.

## Data sources (MVP)

| Source | Endpoint | Key | Status |
|---|---|---|---|
| **K-Startup** (창업진흥원) — *primary* | `…/kisedKstartupService01/getAnnouncementInformation01` (params: `page`, `perPage`, `returnType=json`) | `serviceKey` | ✅ live — 28,758 programs |
| Bizinfo (기업마당) — *secondary* | `bizinfo.go.kr/uss/rss/bizinfoApi.do` | `crtfcKey` | ✅ live — ~500 active |

### Register the keys (links verified 2026-05-22)

- **K-Startup `serviceKey`** — <https://www.data.go.kr/data/15125364/openapi.do> (search box: `창업진흥원 K-Startup 조회서비스`). Click **활용신청** → instant/auto-approved → copy the key. `15125364` is an internal ID: it works in the URL, **not** the search box.
- **Bizinfo `crtfcKey`** — <https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi> (or menu **활용정보 › 정책정보 개방**). Fill the form (기관명/신청자명/이메일/전화/시스템명/IP-or-URL); key is **emailed** to you. No login required.
  - Endpoint params: `crtfcKey`, `dataType=json`, `searchCnt` (0=all), `searchLclasId` (01–09 category — one is 창업), `hashtags`, `pageUnit`, `pageIndex`.

**Deferred** (broad/civic, for later non-biz domains): 보조금24, 정부24, 청년몽땅정보통, MSS PDF.

## Spike findings

**2026-05-22 — reachability:** both endpoints alive; both need a free key.

**2026-05-23 — live data (keys active):**
- **K-Startup = primary.** 28,758 announcements; paging is `page`/`perPage` (not numOfRows/pageNo). Eligibility comes **already structured** — minimal LLM needed:
  - `biz_enyy` (stage: 예비창업자/1년미만/…/10년미만), `biz_trgt_age` (age range), `supt_regin` (region), `supt_biz_clsfc` (category: 사업화/멘토링/시설/판로·해외진출/글로벌/…), `aply_trgt` + `aply_trgt_ctnt` (target + eligibility prose), `aply_excl_trgt_ctnt` (exclusions — industry/financial/legal in samples, *not* nationality), `prch_cnpl_no` (phone), `detl_pg_url`, dates.
- **Bizinfo = secondary.** ~500 active SME programs; eligibility a coarse tag (`trgetNm: 중소기업`), full criteria in the linked 공고.
- **Foreigner-relevance, honestly:** raw 글로벌/해외 keyword match = 177/1000 K-Startup items, but **most 글로벌/해외진출 = OUTBOUND** (Korean firms expanding abroad — CES, expos), not inbound foreign-founder. The genuinely foreigner-relevant slice (인바운드 / 외국인-open) is smaller. Exclusions aren't nationality-based → foreign residents are **eligible for most of the general pool** (inferred); they just don't know it.
- **Premise (resolved):** structured eligibility-*matching* (stage/age/region/category) is the real engine and is viable via K-Startup — the interim "pure-navigation" read was a Bizinfo artifact. Visa/nationality = a flag, not the spine. Build **K-Startup-primary**.

## Run the spike

1. Get the two free keys — see **Register the keys** above. (data.go.kr is instant; Bizinfo emails the key after a short form.)
2. `cp .env.example .env` and paste the keys in.
3. `python3 _scripts/probe_sources.py` (stdlib only, no install). Pulls ~20 records/source and reports: item count, real field names, foreigner-relevant vs national-only term frequency, and contact-field presence.

## Architecture (planned)

Daily cron → pull both APIs → dedupe (fuzzy title + agency + dates) → LLM-parse 지원대상/신청자격 → structured eligibility (new/changed only) → English translation (cached) → paginated static JSON. Frontend: static card-feed (seoulcrushing house style), localStorage state, boolean filter at runtime — **no LLM at runtime.**

## Principles

No runtime LLM (ingestion only) · privacy-first (no analytics/cookies/3rd-party) · honest eligibility confidence (`explicit` / `inferred` / `probable`, always show original Korean) · self-hostable (static CDN + LLM API for ingestion only) · simple surface / comprehensive back end.

## Open decisions

1. ~~**Public name / positioning**~~ — **resolved:** shipped as **Start** (the house pillar) + positioning "Korean startup & business support, in English, for foreign founders." Doesn't lead with the visa filter.
2. **The wow discovery** — feature the standout foreigner-unique programs (OASIS startup-visa, global tracks) + the "293 of 296 state no nationality bar" framing. Partially live; refine.
3. Card valence split (Open-now / Standing recommended) · sources-panel filter (life-domain vs 부처) · timeline panel (deadlines, recommended).
4. ~~**Remote / deploy**~~ — **resolved 2026-05-24:** public repo + its own Cloudflare Pages project + subdomain `start.seoulcrushing.com` (Option A; 301-flippable to a `/start` path later). Full pipeline/runbook in [FAILSAFE.md](./FAILSAFE.md).

---
*Supersedes the original F-5-first planning brief. Key inversions: audience is F-6 / foreign-founder (not F-5); MVP domain is biz-support (not all life domains); contact-as-primary-action retired.*
