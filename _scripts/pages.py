#!/usr/bin/env python3
"""Static per-program overview pages for Korea Programs Navigator.

Emitted by build.py into public/start/<id>.html — one shareable, SEO-able,
English overview per program. Standalone (inline CSS, works on file://).
The feed's cards link here (same tab; back-button returns to the feed).

Pure stdlib. All English labels come from fixed maps (zero LLM); the only
LLM-derived text (title_en/summary_en/target_en/exclusions_en) is precomputed
and faithful — see _scripts/enrich.py + data/translations.json.
"""
from __future__ import annotations

import datetime as dt
import html
import os

STAGE_EN = {"예비창업자": "Pre-launch", "1년미만": "<1yr", "2년미만": "<2yr",
            "3년미만": "<3yr", "5년미만": "<5yr", "7년미만": "<7yr", "10년미만": "<10yr"}
REG_EN = {"전국": "Nationwide", "서울": "Seoul", "경기": "Gyeonggi", "부산": "Busan",
          "대구": "Daegu", "인천": "Incheon", "대전": "Daejeon", "광주": "Gwangju",
          "울산": "Ulsan", "강원": "Gangwon", "충북": "Chungbuk", "충남": "Chungnam",
          "전북": "Jeonbuk", "전남": "Jeonnam", "경북": "Gyeongbuk", "경남": "Gyeongnam",
          "제주": "Jeju", "수도권": "Seoul area"}
CAT_LABEL = {"사업화": "Build", "멘토링ㆍ컨설팅ㆍ교육": "Mentoring", "창업교육": "Education",
             "행사ㆍ네트워크": "Event", "시설ㆍ공간ㆍ보육": "Space", "글로벌": "Global",
             "판로ㆍ해외진출": "Export", "기술개발(R&D)": "R&D", "인력": "Hiring",
             "정책자금": "Grants", "융자ㆍ보증": "Loans"}
CAT_GLOSS = {"사업화": "Cash or in-kind support to commercialize and grow your business.",
             "정책자금": "Government policy funding (grant-type).",
             "융자ㆍ보증": "Loans and credit guarantees — repayable financing, not a grant.",
             "시설ㆍ공간ㆍ보육": "Subsidized or free workspace and incubation.",
             "멘토링ㆍ컨설팅ㆍ교육": "Mentoring, consulting, and education — usually no direct cash.",
             "창업교육": "Startup education and training.",
             "행사ㆍ네트워크": "An event, competition, or networking opportunity.",
             "글로벌": "Support to grow your business internationally.",
             "판로ㆍ해외진출": "Help reaching overseas markets and exporting.",
             "기술개발(R&D)": "R&D funding and support for technology development.",
             "인력": "Hiring and workforce support."}
ORG_EXPLAIN = {"National gov": "Run by central government — a ministry or national agency.",
               "Regional Innovation Center": "A 창조경제혁신센터 — a regional, government-backed startup hub.",
               "City/Province agency": "A local public agency or technopark, run by a city or province.",
               "Public foundation": "A non-profit public foundation or institute.",
               "Private / accelerator": "A private accelerator, VC, or company-run program.",
               "University": "A university startup center or industry–academic program.",
               "Other": "Program operator."}
ENGLISH_HOSTS = ("startup-korea.com", "ksgc.global")

PAGE_CSS = """
@font-face{font-family:'Bagel Fat One';src:url('../fonts/bagel-fat-one/bagel-fat-one-400-091.woff2') format('woff2');font-display:swap}
@font-face{font-family:'Source Sans 3';src:url('../fonts/source-sans-3/source-sans-3-400-006.woff2') format('woff2');font-display:swap}
:root{--pink:#ff52e5;--pink-dk:#ca27b2;--ink:#1a1a1a;--muted:#8c8598;--line:#e9e1d4;--bg:#eef0f4;--card:#fff;--ac:#7c4dd6}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:'Source Sans 3','Apple SD Gothic Neo',-apple-system,sans-serif;-webkit-font-smoothing:antialiased;padding:22px}
.kr{font-family:'Apple SD Gothic Neo',sans-serif}
.wrap{max-width:660px;margin:0 auto}
.back{display:inline-block;font-family:ui-monospace,Menlo,monospace;font-size:11px;font-weight:700;color:var(--muted);text-decoration:none;margin-bottom:16px}
.back:hover{color:var(--pink-dk)}
.sheet{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:26px 28px;box-shadow:0 4px 18px -10px rgba(60,30,50,.25)}
.crumb{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:14px}
.cat{font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;font-family:ui-monospace,Menlo,monospace;padding:3px 8px;border-radius:6px;background:color-mix(in srgb,var(--ac) 18%,transparent);color:var(--ac)}
.badge{font-size:10.5px;font-weight:800;padding:3px 9px;border-radius:999px;background:var(--pink);color:#fff}
.badge.abroad{background:#eaf1ff;color:#2f6bd8}
.close{margin-left:auto;font-family:ui-monospace,Menlo,monospace;font-size:12px;font-weight:800;color:var(--pink-dk)}
h1{font-size:25px;line-height:1.14;font-weight:800;letter-spacing:-.01em}
.kotitle{margin-top:6px;font-size:13px;color:var(--muted)}
.lead{margin-top:14px;font-size:15.5px;line-height:1.5}
.gloss{margin-top:8px;font-size:13px;color:var(--muted);font-style:italic}
.sec{margin-top:22px}
.lab{font-family:ui-monospace,Menlo,monospace;font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.stages{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:9px}
.stages span{font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:999px;background:color-mix(in srgb,var(--ac) 12%,transparent);color:var(--ac)}
.body{font-size:14px;line-height:1.5}
.hint{margin-top:8px;font-size:12.5px;color:var(--muted);background:color-mix(in srgb,var(--pink) 7%,transparent);border-radius:8px;padding:8px 11px}
.src{margin-top:8px;font-size:11.5px;color:var(--muted)}
.facts{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:4px}
.fact{background:var(--card);padding:11px 13px}
.fact .k{font-family:ui-monospace,Menlo,monospace;font-size:9.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.fact .v{font-size:14px;font-weight:600;margin-top:3px}
.runby{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:color-mix(in srgb,var(--ac) 6%,var(--card));border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.runby .org{font-size:14px;font-weight:700}
.runby .ph{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--muted);text-decoration:none}
.runby .ph:hover{color:var(--pink-dk)}
.otype{font-size:11px;font-weight:800;font-family:ui-monospace,Menlo,monospace;padding:3px 9px;border-radius:999px;background:color-mix(in srgb,var(--ac) 16%,transparent);color:var(--ac);margin-left:auto;cursor:help}
.cta{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.btn{flex:1 1 200px;text-align:center;font-weight:800;font-size:14px;text-decoration:none;padding:13px 16px;border-radius:11px}
.btn-p{background:var(--pink);color:#fff}.btn-p:hover{background:var(--pink-dk)}
.btn-s{background:transparent;color:var(--ink);border:1px solid var(--line)}.btn-s:hover{border-color:var(--pink)}
.note{margin-top:20px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;line-height:1.45;color:var(--muted)}
"""


def _fmt_date(iso):
    if not iso:
        return "—"
    try:
        return dt.date.fromisoformat(iso).strftime("%b %d, %Y").replace(" 0", " ")
    except Exception:
        return iso


def _app_lang(p):
    # Only assert English when the apply URL is a known English host — targeting
    # foreigners (inbound_global) does NOT mean the application form is English.
    url = p.get("apply_url") or ""
    if any(h in url for h in ENGLISH_HOSTS):
        return "English supported"
    return "Korean (official portal)"


def render_overview(p, site_url=""):
    e = html.escape
    cat_ko = p.get("category", "")
    catlabel = CAT_LABEL.get(cat_ko, cat_ko)
    title = e(p.get("title_en") or p.get("title_ko") or "")
    summary = e(p.get("summary_en") or "")
    gloss = CAT_GLOSS.get(cat_ko, "")
    amin, amax = p.get("age_min"), p.get("age_max")
    age = f"{amin}–{amax}" if amin and amax else (f"{amin}+" if amin else (f"under {amax}" if amax else ""))
    fore = (p.get("nationality_flag") == "explicit_foreign"
            or p.get("foreigner_relevance") in ("inbound_global", "foreigner_targeted"))
    badge = ('<span class="badge">🛂 For foreign founders</span>' if fore
             else ('<span class="badge abroad">🌏 Abroad / outbound</span>'
                   if p.get("foreigner_relevance") == "outbound_na" else ""))
    stage_html = "".join(f"<span>{e(STAGE_EN[s])}</span>" for s in (p.get("business_stage") or []) if s in STAGE_EN)
    target = e(p.get("target_en") or "")
    excl_raw = p.get("exclusions_en") or ""
    excl = e(excl_raw)
    excl_is_pointer = excl_raw.strip() in ("See the official announcement.", "See the official announcement and attachments.", "See detailed announcement.")
    reg = e(REG_EN.get(p.get("region", ""), p.get("region", "")))
    no_prelaunch = bool(p.get("business_stage")) and "예비창업자" not in p["business_stage"]
    org = e(p.get("agency") or "")
    otype = p.get("org_type", "Other")
    oexp = e(ORG_EXPLAIN.get(otype, ""))
    phone = (p.get("contact_phone") or "").strip()
    apply_url = e(p.get("apply_url") or p.get("detail_url") or "#")
    detail_url = e(p.get("detail_url") or "#")

    parts = []
    parts.append('<a class="back" href="../index.html">← Seoul Crushing / Start</a>')
    parts.append('<article class="sheet">')
    parts.append(f'<div class="crumb"><span class="cat">{e(catlabel)}</span>{badge}'
                 f'<span class="close">closes {_fmt_date(p.get("close_date"))}</span></div>')
    parts.append(f"<h1>{title}</h1>")
    if p.get("title_ko"):
        parts.append(f'<div class="kotitle kr">{e(p["title_ko"])}</div>')
    if summary:
        parts.append(f'<p class="lead">{summary}</p>')
    if gloss:
        parts.append(f'<p class="gloss">{e(gloss)}</p>')

    # Who can apply
    wca = ['<div class="sec"><div class="lab">Who can apply</div>']
    if stage_html:
        wca.append(f'<div class="stages">{stage_html}</div>')
    if target:
        wca.append(f'<p class="body">{target}</p>')
    if no_prelaunch:
        wca.append('<p class="hint">This program is for already-operating businesses — '
                   "verify registration requirements on the official posting.</p>")
    wca.append('<p class="src">Eligibility translated from the official Korean posting — '
               "confirm there before applying.</p></div>")
    parts.append("".join(wca))

    if excl and not excl_is_pointer:  # suppress bare "see the announcement" — adds nothing
        parts.append(f'<div class="sec"><div class="lab">Who\'s excluded</div>'
                     f'<p class="body">{excl}</p></div>')

    # Facts
    facts = [("Region", reg), ("Category", e(catlabel))]
    if age:
        facts.append(("Age", e(age)))
    facts += [("Application", e(_app_lang(p))),
              ("Opens", _fmt_date(p.get("open_date"))),
              ("Closes", _fmt_date(p.get("close_date")))]
    fhtml = "".join(f'<div class="fact"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in facts)
    parts.append(f'<div class="sec"><div class="lab">The facts</div><div class="facts">{fhtml}</div></div>')

    # Run by
    ph = f'<a class="ph" href="tel:{e(phone)}">☎ {e(phone)}</a>' if phone else ""
    parts.append('<div class="sec"><div class="lab">Run by</div>'
                 f'<div class="runby"><div><div class="org">{org}</div>{ph}</div>'
                 f'<span class="otype" title="{oexp}">{e(otype)}</span></div></div>')

    # CTAs
    parts.append('<div class="cta">'
                 f'<a class="btn btn-p" href="{apply_url}" target="_blank" rel="noopener noreferrer">Apply on official site →</a>'
                 f'<a class="btn btn-s" href="{detail_url}" target="_blank" rel="noopener noreferrer">Full announcement (Korean) →</a></div>')

    parts.append('<p class="note">Eligibility and details are drawn from the official Korean announcement and '
                 "translated for navigation — <b>confirm on the official posting before applying.</b> "
                 "Seoul Crushing doesn't decide eligibility and never guarantees you qualify.</p>")
    parts.append("</article>")

    head = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title} — Seoul Crushing</title>'
            f'<meta name="description" content="{summary}">'
            f'<meta property="og:title" content="{title}"><meta property="og:description" content="{summary}">'
            f'<meta property="og:type" content="article">'
            f'<link rel="canonical" href="{site_url}/start/{p["id"]}">'
            f'<meta property="og:url" content="{site_url}/start/{p["id"]}">'
            f"<style>{PAGE_CSS}</style></head><body><div class=\"wrap\">")
    return head + "".join(parts) + "</div></body></html>"


def make_pages(programs, public_dir, site_url=""):
    """Emit public/start/<id>.html for each program AND prune pages for programs
    no longer published (closed / held / removed), so the dir matches the payload
    exactly. Returns the count."""
    out = os.path.join(public_dir, "start")
    os.makedirs(out, exist_ok=True)
    keep, n = set(), 0
    for p in programs:
        pid = p.get("id")
        if not pid:
            continue
        with open(os.path.join(out, f"{pid}.html"), "w", encoding="utf-8") as f:
            f.write(render_overview(p, site_url))
        keep.add(f"{pid}.html")
        n += 1
    if keep:  # never prune to empty (guards against a bad/empty build wiping the dir)
        for fn in os.listdir(out):
            if fn.endswith(".html") and fn not in keep:
                os.remove(os.path.join(out, fn))
    return n


STATS_EXTRA_CSS = """
.lead{margin-top:10px}
.callout{background:linear-gradient(100deg,color-mix(in srgb,var(--pink) 16%,var(--card)),var(--card) 72%);border:1px solid color-mix(in srgb,var(--pink) 34%,var(--line));border-radius:14px;padding:16px 18px;margin-top:16px;font-size:14px;line-height:1.5}
.callout b{font-family:'Bagel Fat One','Arial Black',cursive;color:var(--pink-dk);font-size:20px}
.stat{margin-top:24px}
.stat h2{font-size:11px;font-family:ui-monospace,Menlo,monospace;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:10px;font-weight:800}
.bar{display:flex;align-items:center;gap:10px;margin:5px 0}
.bl{flex:0 0 150px;font-size:12.5px;text-align:right}
.bt{flex:1;height:12px;background:color-mix(in srgb,var(--line) 55%,transparent);border-radius:999px;overflow:hidden}
.bf{display:block;height:100%;background:var(--ac);border-radius:999px}
.bn{flex:0 0 30px;font-size:11.5px;font-weight:700;color:var(--muted);font-family:ui-monospace,Menlo,monospace}
"""


def _bars(counter):
    mx = max(counter.values()) if counter else 1
    return "".join(
        f'<div class="bar"><span class="bl">{html.escape(str(l))}</span>'
        f'<span class="bt"><span class="bf" style="width:{round(c / mx * 100)}%"></span></span>'
        f'<span class="bn">{c}</span></div>'
        for l, c in counter.most_common()
    )


def make_stats(programs, public_dir):
    """Emit public/stats.html — a compact 'by the numbers' view (the 'See it'
    artifact from the 'Build it' data). Static, computed at build time.

    SHELVED: not called by build.py (the 'By the numbers' page is wishlisted;
    its header link was removed). Kept here for revival — rich-stats mock lives
    at _mocks/stats-landscape-wip.html. Re-wire the call in build.py to ship it.
    """
    from collections import Counter
    total = len(programs)
    silent = sum(1 for p in programs if p.get("nationality_flag") == "silent")
    barred = sum(1 for p in programs if p.get("nationality_flag") == "barred")
    cat = Counter(CAT_LABEL.get(p.get("category", ""), p.get("category", "")) for p in programs)
    reg = Counter(REG_EN.get(p.get("region", ""), p.get("region", "")) for p in programs if p.get("region"))
    org = Counter(p.get("org_type", "Other") for p in programs)
    bar_clause = (", and <b>none</b> we found state a nationality bar" if barred == 0
                  else f"; only {barred} state a nationality bar")
    body = (
        '<a class="back" href="index.html">← Seoul Crushing / Start</a>'
        '<article class="sheet"><h1>By the numbers</h1>'
        f'<p class="lead">What {total} live Korean government startup &amp; business-support programs look like — '
        "and how open they are to foreign founders.</p>"
        f'<div class="callout">🛂 <b>{silent}</b> of {total} programs state <b>no nationality requirement</b>'
        f"{bar_clause}. As a legal resident, you can likely apply to far more than you'd expect.</div>"
        f'<div class="stat"><h2>By category</h2>{_bars(cat)}</div>'
        f'<div class="stat"><h2>By region</h2>{_bars(reg)}</div>'
        f'<div class="stat"><h2>Run by</h2>{_bars(org)}</div>'
        '<p class="note">Source: K-Startup (창업진흥원) open data — the current active set, refreshed regularly. '
        "Counts describe the programs in the navigator, not all of Korea's support programs.</p></article>"
    )
    css = PAGE_CSS.replace("../fonts/", "fonts/") + STATS_EXTRA_CSS  # root-level: fonts/ not ../fonts/
    head = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>By the numbers — Seoul Crushing / Start</title>"
        f'<meta name="description" content="What {total} Korean government startup programs look like, '
        'and how open they are to foreign founders.">'
        f"<style>{css}</style></head><body><div class=\"wrap\">"
    )
    with open(os.path.join(public_dir, "stats.html"), "w", encoding="utf-8") as f:
        f.write(head + body + "</div></body></html>")
