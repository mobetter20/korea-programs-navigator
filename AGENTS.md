# AGENTS.md — korea-programs-navigator

Canonical doc: [README.md](README.md). This file adds the tool-agnostic run notes.

## AI steps run on your agent's own compute (never a paid API)

Eligibility parsing happens once at **ingestion** (LLM-parse of K-Startup +
Bizinfo listings → static JSON) — there is **no runtime LLM**; the served site is
static. That ingestion parse runs on whatever agent you're using — Claude Code
subagents, or your agent's own model runs — **never a paid or metered AI API**.
Standing rule: no API keys for AI, no runtime LLM billing. A Codex session
substitutes its own model runs for the parse; the ingestion Python and the static
card-feed frontend are agent-neutral.
