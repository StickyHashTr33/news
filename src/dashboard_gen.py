"""
dashboard_gen.py — Generates docs/index.html
Layout: left topic nav | main content (SAPD → Latest → Topics)
"""

import os
import re
from datetime import datetime
from collections import defaultdict

DOCS_DIR = os.environ.get('DOCS_DIR', 'docs')
SITE_URL  = os.environ.get('SITE_URL', 'https://stickyhashtr33.github.io/news')

TOPIC_COLORS = [
    {"bg":"#E1F5EE","text":"#0F6E56","border":"#5DCAA5"},
    {"bg":"#E6F1FB","text":"#185FA5","border":"#85B7EB"},
    {"bg":"#EEEDFE","text":"#534AB7","border":"#AFA9EC"},
    {"bg":"#FAEEDA","text":"#854F0B","border":"#EF9F27"},
    {"bg":"#EAF3DE","text":"#3B6D11","border":"#97C459"},
    {"bg":"#FAECE7","text":"#993C1D","border":"#F0997B"},
    {"bg":"#FBEAF0","text":"#993556","border":"#ED93B1"},
    {"bg":"#FCEBEB","text":"#A32D2D","border":"#F09595"},
]

SAPD_COLOR = {"bg":"#FEF2F2","text":"#991B1B","border":"#FCA5A5"}

# Macro-groups for the sidebar nav — collapses the flat topic list from
# config/topics.yml into a handful of sections. Any topic not listed here
# (e.g. a newly added one) falls into an auto-generated "Other" group so
# nothing silently disappears from the nav.
TOPIC_GROUPS = {
    "Local & Texas": [
        "Texas Surveillance",
        "Texas & San Antonio Local",
        "ALPR & Flock Cameras",
        "Housing & Gentrification",
        "Texas Environment & Water",
    ],
    "Tech, Privacy & Security": [
        "AI & Automation",
        "Cybersecurity",
        "Digital Rights & Privacy",
        "OSINT & Open Source Intelligence",
        "Open Source Software",
        "Data Center & Grid Infrastructure",
    ],
    "Environment & Nature": [
        "Climate & Environment",
        "Ecology & Conservation",
        "Foraging & Wild Plants",
        "Small Farm & Urban Agriculture",
        "Mycology & Mushrooms",
    ],
    "Health & Medicine": [
        "Diabetes & Kidney Disease",
        "Opioid Treatment & Methadone",
        "Public Health & Health Equity",
        "Psychedelics & Psilocybin Research",
    ],
    "Policy, Justice & Labor": [
        "Immigration & Border",
        "Police & Criminal Justice",
        "Government Accountability",
        "Labor & Worker Rights",
        "Worker Cooperatives & Solidarity Economy",
        "Cannabis, Hemp & Drug Policy",
        "USDA & Farm Grants",
        "Indigenous News & Tribal Sovereignty",
    ],
    "Culture & Ideas": [
        "Hermeticism & Esoteric",
        "Stoicism & Philosophy",
        "Tabletop RPG & D&D",
        "Science & Research",
    ],
}


def _topic_color(index: int) -> dict:
    return TOPIC_COLORS[index % len(TOPIC_COLORS)]


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')


def _reading_time(text: str) -> str:
    words = len((text or '').split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"


def _time_ago(dt_str: str) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        diff = datetime.now(dt.tzinfo) - dt
        minutes = int(diff.total_seconds() / 60)
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        return f"{diff.days}d ago"
    except Exception:
        return ""


def _article_card(a: dict, color: dict) -> str:
    title     = (a.get('title') or 'Untitled')
    url       = a.get('url', '#')
    desc_full = (a.get('description') or '')
    desc      = desc_full[:160]
    publisher = a.get('publisher', '')
    if isinstance(publisher, dict):
        publisher = publisher.get('title', '')
    keyword   = a.get('keyword', '')
    topic     = a.get('topic', '')
    seen_at   = a.get('seen_at', '')
    timeago   = _time_ago(seen_at)
    is_sapd   = a.get('is_sapd', False)
    read_time = _reading_time(f"{title} {desc_full}")
    card_id   = _slug(f"{title}-{seen_at}") or _slug(url)

    maps_url  = a.get('maps_url', url) if is_sapd else url

    return f'''
    <article class="card" data-topic="{_slug(topic)}" data-id="{card_id}" style="border-left:3px solid {color['border']};">
      <button class="bookmark-btn" data-id="{card_id}" title="Save for later" aria-label="Save for later">☆</button>
      <a class="card-title" href="{maps_url}" target="_blank" rel="noopener">{title}</a>
      {f'<p class="card-desc">{desc}</p>' if desc and not is_sapd else ''}
      <div class="card-meta">
        {f'<span class="kw-pill" style="background:{color["bg"]};color:{color["text"]};">{keyword or topic}</span>'}
        {f'<span class="publisher">{publisher}</span>' if publisher and not is_sapd else ''}
        {f'<span class="timeago">{timeago}</span>' if timeago else ''}
        {f'<span class="readtime">{read_time}</span>' if not is_sapd else ''}
      </div>
    </article>'''


def _section(section_id: str, title: str, count_label: str,
             cards_html: str, color: dict) -> str:
    return f'''
    <section class="topic-section" id="{section_id}">
      <div class="topic-header" style="border-bottom:2px solid {color['border']};">
        <h2 class="topic-name" style="color:{color['text']};">{title}</h2>
        <span class="topic-count">{count_label}</span>
      </div>
      <div class="card-grid">{cards_html}</div>
    </section>'''


def generate_dashboard(articles: list[dict], stats: dict = None):
    os.makedirs(DOCS_DIR, exist_ok=True)

    # Split SAPD from news articles
    sapd_articles = [a for a in articles if a.get('is_sapd')]
    news_articles = [a for a in articles if not a.get('is_sapd')]

    # Group news by topic
    by_topic: dict = defaultdict(list)
    for a in news_articles:
        by_topic[a.get('topic', 'Other')].append(a)

    topic_list      = list(by_topic.keys())
    topic_color_map = {t: _topic_color(i) for i, t in enumerate(topic_list)}

    # ── Controls bar: search, SAPD toggle, topic chips, saved-only ───────────
    chips_html = ''.join(
        f'<button class="chip" data-topic="{_slug(t)}" aria-pressed="true">{t}</button>'
        for t in topic_list
    )
    controls = f'''
    <div class="controls">
      <input id="q" class="search" type="search" placeholder="Search headlines… (press /)" autocomplete="off">
      <label class="sapd-toggle"><input type="checkbox" id="sapdToggle" checked> SAPD calls</label>
      <button class="chip-reset" id="savedToggle" aria-pressed="false">☆ Saved only</button>
      <details class="filter-menu">
        <summary>Topics</summary>
        <div class="chip-row">{chips_html}
          <button class="chip-reset" id="chipReset">Reset all</button>
        </div>
      </details>
    </div>'''

    # ── Left sidebar nav ─────────────────────────────────────────────────────
    def nav_item(href: str, label: str, color: dict, count: int = 0) -> str:
        badge = f'<span class="nav-badge" style="background:{color["border"]};color:#fff;">{count}</span>' if count else ''
        return (f'<a class="nav-link" href="#{href}" '
                f'style="border-left:3px solid {color["border"]};color:{color["text"]};background:{color["bg"]};">'
                f'{label}{badge}</a>')

    nav_html = nav_item('sapd', '🚨 SAPD Calls', SAPD_COLOR, len(sapd_articles))
    nav_html += nav_item('latest', '⚡ Latest', {"bg":"#f3f4f6","text":"#374151","border":"#1a1a18"}, len(news_articles[:30]))

    # ── Grouped topic nav: macro-categories, collapsible ──────────────────────
    topic_index = {t: i for i, t in enumerate(topic_list)}
    grouped_seen = set()
    nav_groups_html = ''

    def _group_block(group_name: str, topics_in_group: list) -> str:
        items_html = ''
        group_count = 0
        for t in topics_in_group:
            if t not in by_topic:
                continue
            i = topic_index[t]
            c = topic_color_map[t]
            items_html += nav_item(f'topic-{i}', t, c, len(by_topic[t]))
            group_count += len(by_topic[t])
            grouped_seen.add(t)
        if not items_html:
            return ''
        return f'''
        <details class="nav-group" data-group="{_slug(group_name)}">
          <summary class="nav-group-summary">{group_name}<span class="nav-group-count">{group_count}</span></summary>
          <div class="nav-group-items">{items_html}</div>
        </details>'''

    for group_name, topics_in_group in TOPIC_GROUPS.items():
        nav_groups_html += _group_block(group_name, topics_in_group)

    leftover = [t for t in topic_list if t not in grouped_seen]
    if leftover:
        nav_groups_html += _group_block('Other', leftover)

    # ── SAPD section ─────────────────────────────────────────────────────────
    if sapd_articles:
        sapd_cards = ''.join(_article_card(a, SAPD_COLOR) for a in sapd_articles[:50])
        sapd_section = _section('sapd', '🚨 SAPD Calls for Service',
                                f'{len(sapd_articles)} active call{"s" if len(sapd_articles)!=1 else ""}',
                                sapd_cards, SAPD_COLOR)
    else:
        sapd_section = ''

    # ── Latest section ───────────────────────────────────────────────────────
    latest = sorted(news_articles, key=lambda a: a.get('seen_at', ''), reverse=True)[:30]
    latest_color = {"bg":"#f3f4f6","text":"#1a1a18","border":"#1a1a18"}
    latest_cards = ''.join(
        _article_card(a, topic_color_map.get(a.get('topic',''), TOPIC_COLORS[0]))
        for a in latest
    )
    latest_section = _section('latest', '⚡ Latest', '30 most recent', latest_cards, latest_color)

    # ── Topic sections ───────────────────────────────────────────────────────
    topic_sections = ''
    for i, (topic, items) in enumerate(by_topic.items()):
        color = topic_color_map[topic]
        cards = ''.join(_article_card(a, color) for a in items[:30])
        topic_sections += _section(f'topic-{i}', topic,
                                   f'{len(items)} article{"s" if len(items)!=1 else ""}',
                                   cards, color)

    all_sections = sapd_section + latest_section + topic_sections

    # ── Ticker ───────────────────────────────────────────────────────────────
    ticker_items = ''
    for a in (sapd_articles[:5] + latest[:20]):
        topic  = a.get('topic', '')
        c      = SAPD_COLOR if a.get('is_sapd') else topic_color_map.get(topic, TOPIC_COLORS[0])
        link   = a.get('maps_url', a.get('url', '#')) if a.get('is_sapd') else a.get('url', '#')
        ticker_items += (
            f'<span class="tick-item">'
            f'<span class="tick-topic" style="color:{c["border"]};">{topic}</span>'
            f'<a href="{link}" target="_blank" rel="noopener">{(a.get("title") or "")[:80]}</a>'
            f'</span>'
        )

    total   = stats.get('total', len(articles)) if stats else len(articles)
    last24h = stats.get('last_24h', '—') if stats else '—'
    updated = datetime.utcnow().strftime('%B %d, %Y · %H:%M UTC')

    n_sources = len(set(
        a.get('publisher', {}).get('title', '') if isinstance(a.get('publisher'), dict)
        else str(a.get('publisher', ''))
        for a in news_articles
    ))

    empty_state = (
        '<div style="text-align:center;padding:60px 20px;color:#aaa;">'
        '<p style="font-family:Playfair Display,serif;font-size:20px;color:#555;">No articles yet</p>'
        '<p>Run the monitor to start collecting.</p></div>'
    )
    main_content = empty_state if not articles else all_sections

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NewsWatch</title>
  <link rel="alternate" type="application/rss+xml" title="NewsWatch" href="feed.xml">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html{{scroll-behavior:smooth}}
    body{{background:#FAFAF8;color:#1a1a18;font-family:'Inter',system-ui,sans-serif;font-size:14px;line-height:1.6}}
    a{{color:inherit;text-decoration:none}}
    a:hover{{text-decoration:underline}}

    /* Ticker */
    .ticker-wrap{{background:#111;overflow:hidden;white-space:nowrap;height:32px;display:flex;align-items:center}}
    .ticker-label{{background:#c0392b;color:#fff;font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;padding:0 12px;height:100%;display:flex;align-items:center;flex-shrink:0}}
    .ticker-track{{display:inline-flex;animation:ticker 180s linear infinite}}
    .tick-item{{display:inline-flex;align-items:center;gap:8px;padding:0 20px;border-right:1px solid #2a2a2a;font-size:11px;color:#888}}
    .tick-item a{{color:#ddd;font-size:11px}}
    .tick-item a:hover{{color:#fff;text-decoration:none}}
    .tick-topic{{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1px;text-transform:uppercase}}
    @keyframes ticker{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}

    /* Masthead */
    .masthead{{border-bottom:2px solid #1a1a18;padding:16px 24px}}
    .masthead-inner{{display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px}}
    .wordmark{{font-family:'Playfair Display',Georgia,serif;font-size:32px;font-weight:900;letter-spacing:-1px;line-height:1}}
    .wordmark em{{font-style:normal;color:#c0392b}}
    .tagline{{font-size:10px;color:#aaa;font-family:'JetBrains Mono',monospace;letter-spacing:1.5px;text-transform:uppercase;margin-left:12px}}
    .masthead-right{{display:flex;align-items:center;gap:24px}}
    .stat-block{{text-align:right}}
    .stat-num{{font-family:'Playfair Display',serif;font-size:20px;font-weight:700;line-height:1}}
    .stat-lbl{{font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:1px;font-family:'JetBrains Mono',monospace}}
    .mh-links{{display:flex;gap:8px}}
    .mh-links a{{font-size:11px;color:#666;border:1px solid #ddd;padding:4px 10px;border-radius:4px}}
    .mh-links a:hover{{border-color:#1a1a18;color:#1a1a18;text-decoration:none}}

    /* Dateline */
    .dateline{{padding:6px 24px;border-bottom:1px solid #E8E5DF;font-family:'JetBrains Mono',monospace;font-size:10px;color:#aaa;display:flex;align-items:center;gap:6px;background:#FAFAF8}}
    .live-dot{{width:6px;height:6px;background:#2ecc71;border-radius:50%;display:inline-block;animation:pulse 2s ease-in-out infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}

    /* Controls bar */
    .controls{{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;gap:12px;align-items:center;
      padding:10px 24px;background:#FAFAF8;border-bottom:1px solid #E8E5DF}}
    .search{{flex:1;min-width:200px;max-width:420px;padding:8px 12px;border:1px solid #ddd;border-radius:6px;
      font-family:'Inter',sans-serif;font-size:13px;background:#fff;color:#1a1a18}}
    .search:focus{{outline:none;border-color:#1a1a18}}
    .sapd-toggle{{font-size:12px;color:#666;display:flex;align-items:center;gap:5px;cursor:pointer}}
    .filter-menu summary{{cursor:pointer;font-size:12px;color:#666;list-style:none;
      border:1px solid #ddd;padding:6px 12px;border-radius:6px}}
    .filter-menu summary::-webkit-details-marker{{display:none}}
    .filter-menu[open] summary{{border-color:#1a1a18;color:#1a1a18}}
    .chip-row{{display:flex;flex-wrap:wrap;gap:6px;padding:12px 0;max-width:720px}}
    .chip{{font-size:11px;padding:4px 10px;border:1px solid #ddd;border-radius:14px;background:#fff;cursor:pointer;
      font-family:'Inter',sans-serif;color:#333;transition:all .1s}}
    .chip[aria-pressed="false"]{{opacity:.4;text-decoration:line-through}}
    .chip-reset{{font-size:11px;padding:4px 10px;border:1px solid #c0392b;color:#c0392b;border-radius:14px;
      background:#fff;cursor:pointer;font-family:'Inter',sans-serif}}
    #savedToggle{{border-color:#ddd;color:#666}}
    #savedToggle[aria-pressed="true"]{{border-color:#e0a800;color:#a67c00;background:#fffbea}}
    .load-more{{grid-column:1/-1;justify-self:center;margin-top:8px;padding:8px 20px;border:1px solid #ddd;
      background:#fff;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;color:#555}}
    .load-more:hover{{border-color:#1a1a18;color:#1a1a18}}

    /* Layout: left nav + main */
    .layout{{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 120px)}}

    /* Left sidebar nav */
    .left-nav{{
      border-right:1px solid #E8E5DF;
      background:#fff;
      position:sticky;
      top:0;
      height:100vh;
      overflow-y:auto;
      padding:16px 0 24px;
      display:flex;
      flex-direction:column;
      gap:3px;
    }}
    .nav-section-label{{
      font-family:'JetBrains Mono',monospace;
      font-size:9px;
      letter-spacing:2px;
      text-transform:uppercase;
      color:#bbb;
      padding:10px 16px 4px;
    }}
    .nav-link{{
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding:8px 14px 8px 13px;
      font-size:12px;
      font-weight:500;
      border-left:3px solid transparent;
      transition:opacity 0.1s;
      margin:0 8px;
      border-radius:0 4px 4px 0;
    }}
    .nav-link:hover{{opacity:0.8;text-decoration:none}}
    .nav-badge{{
      font-size:9px;
      font-family:'JetBrains Mono',monospace;
      padding:1px 5px;
      border-radius:10px;
      min-width:18px;
      text-align:center;
    }}
    .nav-group{{margin:0 8px}}
    .nav-group-summary{{
      display:flex;
      align-items:center;
      justify-content:space-between;
      list-style:none;
      cursor:pointer;
      padding:8px 6px 8px 8px;
      font-size:11px;
      font-weight:600;
      color:#555;
      border-radius:4px;
    }}
    .nav-group-summary::-webkit-details-marker{{display:none}}
    .nav-group-summary::before{{content:'▸';font-size:9px;color:#bbb;margin-right:6px}}
    .nav-group[open] > .nav-group-summary::before{{content:'▾'}}
    .nav-group-summary:hover{{background:#f5f4f1}}
    .nav-group-count{{
      font-size:9px;
      font-family:'JetBrains Mono',monospace;
      color:#bbb;
      margin-left:auto;
    }}
    .nav-group-items{{display:flex;flex-direction:column;gap:2px;padding-left:6px}}

    /* Main content */
    .main-col{{padding:24px 28px}}

    /* Topic sections */
    .topic-section{{margin-bottom:44px}}
    .topic-header{{display:flex;align-items:baseline;justify-content:space-between;padding-bottom:10px;margin-bottom:16px}}
    .topic-name{{font-family:'Playfair Display',Georgia,serif;font-size:20px;font-weight:700}}
    .topic-count{{font-family:'JetBrains Mono',monospace;font-size:10px;color:#aaa;letter-spacing:1px}}
    .card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}

    /* Cards */
    .card{{position:relative;background:#fff;border:1px solid #E8E5DF;border-radius:6px;padding:13px 30px 11px 15px;transition:border-color 0.15s}}
    .card:hover{{border-color:#bbb}}
    .card.kb-focus{{border-color:#1a1a18;box-shadow:0 0 0 2px rgba(26,26,24,0.12)}}
    .card-title{{display:block;font-size:13px;font-weight:500;line-height:1.45;color:#1a1a18;margin-bottom:6px}}
    .card-title:hover{{text-decoration:underline}}
    .card-desc{{font-size:12px;color:#888;line-height:1.5;margin-bottom:8px}}
    .card-meta{{display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
    .kw-pill{{font-size:10px;font-family:'JetBrains Mono',monospace;padding:2px 6px;border-radius:3px}}
    .publisher{{font-size:11px;color:#bbb}}
    .timeago{{font-size:10px;color:#ccc;margin-left:auto;font-family:'JetBrains Mono',monospace}}
    .readtime{{font-size:10px;color:#ccc;font-family:'JetBrains Mono',monospace}}
    .bookmark-btn{{position:absolute;top:10px;right:8px;border:none;background:none;cursor:pointer;
      font-size:15px;line-height:1;color:#ccc;padding:2px}}
    .bookmark-btn:hover{{color:#e0a800}}
    .bookmark-btn.is-saved{{color:#e0a800}}

    /* Footer */
    .footer{{
      border-top:1px solid #E8E5DF;
      padding:14px 24px;
      font-size:11px;
      color:#bbb;
      font-family:'JetBrains Mono',monospace;
      display:flex;
      justify-content:space-between;
      align-items:center;
      flex-wrap:wrap;
      gap:8px;
    }}
    .built-by{{color:#aaa;font-size:11px}}
    .built-by span{{color:#c0392b;font-weight:500}}

    /* Responsive */
    @media(max-width:768px){{
      .layout{{grid-template-columns:1fr}}
      .left-nav{{display:none}}
      .masthead{{padding:12px 16px}}
      .main-col{{padding:16px}}
      .masthead-right{{display:none}}
      .card-grid{{grid-template-columns:1fr}}
    }}
    @media(prefers-reduced-motion:reduce){{
      .ticker-track{{animation:none}}
      .live-dot{{animation:none}}
    }}
  </style>
</head>
<body>

<div class="ticker-wrap">
  <div class="ticker-label">Live</div>
  <div style="overflow:hidden;flex:1;">
    <div class="ticker-track">{ticker_items}{ticker_items}</div>
  </div>
</div>

<header class="masthead">
  <div class="masthead-inner">
    <div style="display:flex;align-items:baseline">
      <div class="wordmark">News<em>Watch</em></div>
      <div class="tagline">San Antonio · Independent</div>
    </div>
    <div class="masthead-right">
      <div class="stat-block"><div class="stat-num">{total}</div><div class="stat-lbl">Total</div></div>
      <div class="stat-block"><div class="stat-num">{last24h}</div><div class="stat-lbl">24h</div></div>
      <div class="stat-block"><div class="stat-num">{len(sapd_articles)}</div><div class="stat-lbl">SAPD</div></div>
      <div class="mh-links">
        <a href="feed.xml">RSS</a>
        <a href="https://github.com/StickyHashTr33/news" target="_blank">GitHub</a>
      </div>
    </div>
  </div>
</header>

<div class="dateline">
  <span class="live-dot"></span>
  <span>Updated {updated}</span>
  <span style="color:#ddd">·</span>
  <span>{len(topic_list)} topics · {n_sources} sources</span>
</div>
{controls}
<div class="layout">

  <nav class="left-nav" aria-label="Topics">
    <div class="nav-section-label">Sections</div>
    {nav_html}
    <div class="nav-section-label">Topics</div>
    {nav_groups_html}
  </nav>

  <main class="main-col">
    {main_content}
  </main>

</div>

<footer class="footer">
  <div class="built-by">Built by <span>Lou</span> · NewsWatch · GitHub Actions</div>
  <a href="feed.xml" style="color:#bbb;">Subscribe via RSS</a>
</footer>

<script>
(function(){{
  const PAGE = 15, HIDDEN_KEY = 'nw_hidden_topics', SAVED_KEY = 'nw_saved';
  let hidden = new Set(); try {{ hidden = new Set(JSON.parse(localStorage.getItem(HIDDEN_KEY)||'[]')); }} catch(e){{}}
  let saved  = new Set(); try {{ saved  = new Set(JSON.parse(localStorage.getItem(SAVED_KEY)||'[]')); }} catch(e){{}}
  const saveHidden = () => localStorage.setItem(HIDDEN_KEY, JSON.stringify([...hidden]));
  const saveSaved  = () => localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));

  const q = document.getElementById('q');
  const cards = [...document.querySelectorAll('.card')];
  let savedOnly = false;

  // pagination: hide overflow per grid, add a Load More button
  document.querySelectorAll('.card-grid').forEach(grid => {{
    const c = [...grid.querySelectorAll('.card')];
    if (c.length <= PAGE) return;
    c.slice(PAGE).forEach(x => x.dataset.paged = '0');
    const btn = document.createElement('button');
    btn.className = 'load-more';
    btn.textContent = 'Load ' + (c.length - PAGE) + ' more';
    btn.onclick = () => {{ c.forEach(x => x.dataset.paged = '1'); btn.remove(); refresh(); }};
    grid.appendChild(btn);
  }});

  function visible(card){{
    const term = (q.value||'').trim().toLowerCase();
    if (hidden.has(card.dataset.topic)) return false;
    if (savedOnly && !saved.has(card.dataset.id)) return false;
    if (term && !card.textContent.toLowerCase().includes(term)) return false;
    if (!term && card.dataset.paged === '0') return false;   // pagination only when not searching
    return true;
  }}
  function refresh(){{ cards.forEach(c => c.style.display = visible(c) ? '' : 'none'); }}

  q.addEventListener('input', refresh);

  document.querySelectorAll('.chip').forEach(chip => {{
    const t = chip.dataset.topic;
    if (hidden.has(t)) chip.setAttribute('aria-pressed','false');
    chip.onclick = () => {{
      if (hidden.has(t)) {{ hidden.delete(t); chip.setAttribute('aria-pressed','true'); }}
      else {{ hidden.add(t); chip.setAttribute('aria-pressed','false'); }}
      saveHidden(); refresh();
    }};
  }});
  const reset = document.getElementById('chipReset');
  if (reset) reset.onclick = () => {{
    hidden.clear(); saveHidden();
    document.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed','true'));
    refresh();
  }};

  const sapd = document.getElementById('sapdToggle'), sapdSec = document.getElementById('sapd');
  if (sapd && sapdSec) sapd.onchange = () => {{ sapdSec.style.display = sapd.checked ? '' : 'none'; }};

  // Bookmarks
  document.querySelectorAll('.bookmark-btn').forEach(btn => {{
    const id = btn.dataset.id;
    if (saved.has(id)) {{ btn.textContent = '★'; btn.classList.add('is-saved'); }}
    btn.onclick = (e) => {{
      e.preventDefault(); e.stopPropagation();
      if (saved.has(id)) {{ saved.delete(id); btn.textContent = '☆'; btn.classList.remove('is-saved'); }}
      else {{ saved.add(id); btn.textContent = '★'; btn.classList.add('is-saved'); }}
      saveSaved(); if (savedOnly) refresh();
    }};
  }});
  const savedToggle = document.getElementById('savedToggle');
  if (savedToggle) savedToggle.onclick = () => {{
    savedOnly = !savedOnly;
    savedToggle.setAttribute('aria-pressed', String(savedOnly));
    savedToggle.textContent = savedOnly ? '★ Saved only' : '☆ Saved only';
    refresh();
  }};

  // Keyboard shortcuts: j/k move between visible cards, Enter opens, / focuses search
  let focusIdx = -1;
  function visibleCards(){{ return cards.filter(c => c.style.display !== 'none'); }}
  function setFocus(idx){{
    const vc = visibleCards();
    if (!vc.length) return;
    if (focusIdx >= 0 && vc[focusIdx]) vc[focusIdx].classList.remove('kb-focus');
    focusIdx = ((idx % vc.length) + vc.length) % vc.length;
    const el = vc[focusIdx];
    el.classList.add('kb-focus');
    el.scrollIntoView({{block:'center', behavior:'smooth'}});
  }}
  document.addEventListener('keydown', (e) => {{
    if (e.target === q) {{
      if (e.key === 'Escape') q.blur();
      return;
    }}
    if (e.key === '/') {{ e.preventDefault(); q.focus(); return; }}
    if (e.key === 'j') {{ setFocus(focusIdx + 1); return; }}
    if (e.key === 'k') {{ setFocus(focusIdx - 1); return; }}
    if (e.key === 'Enter') {{
      const vc = visibleCards();
      const el = vc[focusIdx];
      if (el) {{ const a = el.querySelector('.card-title'); if (a) window.open(a.href, '_blank'); }}
    }}
  }});

  // Nav group accordion state
  const GROUPS_KEY = 'nw_open_groups';
  let openGroups = new Set(); try {{ openGroups = new Set(JSON.parse(localStorage.getItem(GROUPS_KEY)||'[]')); }} catch(e){{}}
  document.querySelectorAll('.nav-group').forEach((grp, idx) => {{
    const key = grp.dataset.group;
    if (openGroups.has(key)) grp.setAttribute('open', '');
    grp.addEventListener('toggle', () => {{
      if (grp.open) openGroups.add(key); else openGroups.delete(key);
      localStorage.setItem(GROUPS_KEY, JSON.stringify([...openGroups]));
    }});
  }});

  refresh();
}})();
</script>

</body>
</html>'''

    out_path = os.path.join(DOCS_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[dashboard] {out_path} — {len(sapd_articles)} SAPD + {len(news_articles)} news, {len(topic_list)} topics")
