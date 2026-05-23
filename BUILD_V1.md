# v1 build contract — locked 2026-05-23

Read **README.md** (North-Star + principles) and **DESIGN.md** (schema, pipeline, parse rules, trust guards) first. Visual spec = open **`public/playground.html`** + **`public/mock.html`** in a browser. This file = the final v1 scope decisions on top of those.

**Build in-place on `main` — no worktree** (solo, no-remote repo). Sonnet tier. Commit at logical boundaries; local only, never add a remote / push.

## Audience
Foreign founders **broadly** — any foreign resident who can register/run a business (F-6 / F-5 / F-2 …) **and** prospective founders abroad (visa-track). **Not F-6-only.** No visa gate, no entry form — everyone browses the same feed; visa relevance shows **per-card** (🛂 Visa lens). Positioning: "for foreign founders in Korea," never "for F-6."

## Data
K-Startup **active only** (~296; `rcrt_prgs_yn=="Y"` AND `close_date ≥ today`). **No Bizinfo** (→ v2). Daily refresh.

## UX (match the playground/mock)
- **Browse:** compact cards, **chips** category color (not rainbow tints, not mono), fat **pink D-day**, warm English title leads + KO secondary. Lenses: `All · 🔥 Closing soon · 🛂 Visa · 💰 Money · 🏢 Space · 🎉 Fun · 🌏 Go global`.
- **⚡ Just-in:** recency stream (newest first) — de-duplicated from the cards (different angle, not the same list).
- **View customization:** **Light** (default = gray bg · 3-col · stream on) / **Dark** (dark · 3 · on) / **Custom** (bg `gray|pink|dark` · cols `2|3|4` · stream `on|off`). Persist in localStorage. Color = chips only.
  - _Amended 2026-05-24: default cols 4 → 3. At a typical ~900px Arc window 4-col yielded ~138px cards (titles wrapping 4–5 lines); 3-col (~190px) matches the playground feel that was signed off. 4-col remains available in Custom._
- **Wow discovery (in v1):** feature the standout foreigner-unique programs prominently (OASIS startup-visa, global tracks) — a featured slot + 🛂 Visa as a front lens. This is the shareable hook ("wait, I can get a startup visa?!"). No new data — pure framing of what's already in the 296.

## Translation — NO paid AI API
`title_ko` + `summary_ko` → **warm, human, plain English** (not literal gov-speak; match the tone in `mock.html`), + inbound/outbound tag for `글로벌` / `판로ㆍ해외진출` categories. Do it via **Claude Code** (Haiku subagents, or inline if running as one) — cache to `data/translations.json` keyed by `content_hash`, deltas only. (Owner rule `feedback_no_paid_ai_api`.)

## Also in v1
**RSS feed** — static `feed.xml` emitted by `build.py` (no backend, no PII; fits privacy-first + serves don't-miss-out).

## Explicitly NOT in v1
- Bizinfo (→ v2, only if users ask for SME/소상공인/financing breadth)
- Email/subscription (PII + send infra — against static/privacy-first)
- Saved / applied / remind-me (off-North-Star: we're a navigation aid that links **out** to apply, not a personal tracker; deadline-sort + RSS already cover "don't miss it")
- Other life-domains / sources (→ v3+)

## Roadmap context
v1.x: the wow-anchor landing page · RSS polish. v2: Bizinfo (gated on signal) · content personalization (pin/hide lenses). v3+: other domains (보조금24/정부24 — housing/family/tax) + the 다문화 family layer.
