# Korea Programs Navigator

> **Working title.** Public name is a launch-time decision (see Open decisions). Don't pitch the visa filter — pitch the user's problem: *Korea's startup/business support, navigable, in English.*

English-language navigator that aggregates Korean government **startup & business-support** programs from open APIs and surfaces what a **foreign resident** can actually apply for. Comprehensive underneath, one scannable card per program on top. Visual/architecture sibling: [seoulcrushing.com](../seoulcrushing.com).

## North-Star

Make Korea's startup- and business-support universe **navigable** for foreign residents who want to start or run something here but can't find — or read — what's open to them. Surface what they can actually apply for, in plain English, from data they can **trust**. Comprehensive underneath, ruthlessly simple on top: one program = one scannable card, never a menu you fight. A navigation aid that shows you what exists and how to verify it — never an adjudicator that promises you qualify.

**Drift signals:** (a) coverage gaps that hollow out "comprehensive"; (b) the surface going layered as coverage grows — *simple wins the top, comprehensive the back end*; (c) data that doesn't earn trust (stale, unsourced, falsely certain); (d) implying eligibility certainty the prose doesn't support; (e) drifting toward Korean-national startup tooling or general expat/tourist content; (f) any runtime LLM, analytics, or tracking.

## Audience & scope (MVP)

- **Audience A — foreign-resident founders.** People on F-6 / F-5 / F-2 etc. who want to start or run a business in Korea. User-zero: project owner (F-6).
- **Domain: entrepreneurship / startup / business-support only.** Rides the two richest sources; broader civic aggregators deferred.
- **다문화 / 결혼이민 entrepreneur programs** are a *featured high-confidence sub-set* (explicit eligibility language → "wow discovery" candidate), not the product's headline.
- **Contact info** is captured and shown when present, but carries no weight — not the primary CTA. (Brief's "contact-as-primary-action" principle retired.)
- English only at launch.

## Data sources (MVP)

| Source | Endpoint | Key | Status |
|---|---|---|---|
| K-Startup (창업진흥원) | `apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01` | `serviceKey` (data.go.kr) | live, **needs key** |
| Bizinfo (기업마당) | `bizinfo.go.kr/uss/rss/bizinfoApi.do` | `crtfcKey` (bizinfo.go.kr) | live, **needs key** |

### Register the keys (links verified 2026-05-22)

- **K-Startup `serviceKey`** — <https://www.data.go.kr/data/15125364/openapi.do> (search box: `창업진흥원 K-Startup 조회서비스`). Click **활용신청** → instant/auto-approved → copy the key. `15125364` is an internal ID: it works in the URL, **not** the search box.
- **Bizinfo `crtfcKey`** — <https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi> (or menu **활용정보 › 정책정보 개방**). Fill the form (기관명/신청자명/이메일/전화/시스템명/IP-or-URL); key is **emailed** to you. No login required.
  - Endpoint params: `crtfcKey`, `dataType=json`, `searchCnt` (0=all), `searchLclasId` (01–09 category — one is 창업), `hashtags`, `pageUnit`, `pageIndex`.

**Deferred** (broad/civic, for later non-biz domains): 보조금24, 정부24, 청년몽땅정보통, MSS PDF.

## Spike findings (2026-05-22)

- Both endpoints **reachable and alive**; both require a **free auth key** (Bizinfo returns `인증키를 입력해주세요`; K-Startup returns `401 Unauthorized`).
- **Both sources confirmed to carry 지원대상 (eligibility) + 문의처 (contact) + 신청기간 (period)** — so visa-aware filtering and contact capture are both supported by the data model.
  - K-Startup (semantic, from data description): 사업명 / 사업유형 / 사업개요 / 지원대상 / 모집기간 / 신청방법 / 문의처.
  - Bizinfo (exact field names): `pblancId` (dedup key) / `title` / `trgetNm` (지원대상) / `refrncNm` (문의처) / `reqstBeginEndDe` (신청기간) / `jrsdInsttNm` (소관기관) / `pldirSportRealmLclasCodeNm` (지원분야) / `bsnsSumryCn` (개요) / `reqstMthPapersCn` (신청방법).
- **Verdict: data premise SOUND, pending 2 free keys.**

## Run the spike

1. Get the two free keys — see **Register the keys** above. (data.go.kr is instant; Bizinfo emails the key after a short form.)
2. `cp .env.example .env` and paste the keys in.
3. `python3 _scripts/probe_sources.py` (stdlib only, no install). Pulls ~20 records/source and reports: item count, real field names, foreigner-relevant vs national-only term frequency, and contact-field presence.

## Architecture (planned)

Daily cron → pull both APIs → dedupe (fuzzy title + agency + dates) → LLM-parse 지원대상/신청자격 → structured eligibility (new/changed only) → English translation (cached) → paginated static JSON. Frontend: static card-feed (seoulcrushing house style), localStorage state, boolean filter at runtime — **no LLM at runtime.**

## Principles

No runtime LLM (ingestion only) · privacy-first (no analytics/cookies/3rd-party) · honest eligibility confidence (`explicit` / `inferred` / `probable`, always show original Korean) · self-hostable (static CDN + LLM API for ingestion only) · simple surface / comprehensive back end.

## Open decisions

1. **Public name / positioning** — should emerge from the "wow discovery"; don't lead with the visa filter.
2. **The wow discovery** — find one foreigner-eligible biz program ~80% qualify for and ~80% don't know about. Landing-page + launch anchor.
3. Card valence split (Open-now / Standing recommended) · sources-panel filter (life-domain vs 부처) · timeline panel (deadlines, recommended).
4. **Remote / deploy** — local-only for now (privacy default; no remote added). seoulcrushing.com uses a `mobetter20` GitHub + Cloudflare Pages — the obvious path when ready, but the owner's call.

---
*Supersedes the original F-5-first planning brief. Key inversions: audience is F-6 / foreign-founder (not F-5); MVP domain is biz-support (not all life domains); contact-as-primary-action retired.*
