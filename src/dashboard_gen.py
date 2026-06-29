"""
dashboard_gen.py — Generates docs/index.html
Layout: left topic nav | main content (SAPD → Latest → Topics)
"""

import os
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


def _topic_color(index: int) -> dict:
    return TOPIC_COLORS[index % len(TOPIC_COLORS)]


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
    desc      = (a.get('description') or '')[:160]
    publisher = a.get('publisher', '')
    if isinstance(publisher, dict):
        publisher = publisher.get('title', '')
    keyword   = a.get('keyword', '')
    topic     = a.get('topic', '')
    seen_at   = a.get('seen_at', '')
    timeago   = _time_ago(seen_at)
    is_sapd   = a.get('is_sapd', False)

    maps_url  = a.get('maps_url', url) if is_sapd else url

    return f'''
    <article class="card" style="border-left:3px solid {color['border']};">
      <a class="card-title" href="{maps_url}" target="_blank" rel="noopener">{title}</a>
      {f'<p class="card-desc">{desc}</p>' if desc and not is_sapd else ''}
      <div class="card-meta">
        {f'<span class="kw-pill" style="background:{color["bg"]};color:{color["text"]};">{keyword or topic}</span>'}
        {f'<span class="publisher">{publisher}</span>' if publisher and not is_sapd else ''}
        {f'<span class="timeago">{timeago}</span>' if timeago else ''}
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

    # ── Left sidebar nav ─────────────────────────────────────────────────────
    def nav_item(href: str, label: str, color: dict, count: int = 0) -> str:
        badge = f'<span class="nav-badge" style="background:{color["border"]};color:#fff;">{count}</span>' if count else ''
        return (f'<a class="nav-link" href="#{href}" '
                f'style="border-left:3px solid {color["border"]};color:{color["text"]};background:{color["bg"]};">'
                f'{label}{badge}</a>')

    nav_html = nav_item('sapd', '🚨 SAPD Calls', SAPD_COLOR, len(sapd_articles))
    nav_html += nav_item('latest', '⚡ Latest', {"bg":"#f3f4f6","text":"#374151","border":"#1a1a18"}, len(news_articles[:30]))
    for i, t in enumerate(topic_list):
        c = topic_color_map[t]
        nav_html += nav_item(f'topic-{i}', t, c, len(by_topic[t]))

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

    /* Main content */
    .main-col{{padding:24px 28px}}

    /* Topic sections */
    .topic-section{{margin-bottom:44px}}
    .topic-header{{display:flex;align-items:baseline;justify-content:space-between;padding-bottom:10px;margin-bottom:16px}}
    .topic-name{{font-family:'Playfair Display',Georgia,serif;font-size:20px;font-weight:700}}
    .topic-count{{font-family:'JetBrains Mono',monospace;font-size:10px;color:#aaa;letter-spacing:1px}}
    .card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}

    /* Cards */
    .card{{background:#fff;border:1px solid #E8E5DF;border-radius:6px;padding:13px 13px 11px 15px;transition:border-color 0.15s}}
    .card:hover{{border-color:#bbb}}
    .card-title{{display:block;font-size:13px;font-weight:500;line-height:1.45;color:#1a1a18;margin-bottom:6px}}
    .card-title:hover{{text-decoration:underline}}
    .card-desc{{font-size:12px;color:#888;line-height:1.5;margin-bottom:8px}}
    .card-meta{{display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
    .kw-pill{{font-size:10px;font-family:'JetBrains Mono',monospace;padding:2px 6px;border-radius:3px}}
    .publisher{{font-size:11px;color:#bbb}}
    .timeago{{font-size:10px;color:#ccc;margin-left:auto;font-family:'JetBrains Mono',monospace}}

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
  <span>{len(topic_list)} topics · {len(set(a.get("publisher","") if isinstance(a.get("publisher"),"") else (a.get("publisher") or {{}}).get("title","") for a in news_articles))} sources</span>
</div>

<div class="layout">

  <nav class="left-nav" aria-label="Topics">
    <div class="nav-section-label">Sections</div>
    {nav_html}
  </nav>

  <main class="main-col">
    {'<div style="text-align:center;padding:60px 20px;color:#aaa;"><p style=\'font-family:Playfair Display,serif;font-size:20px;color:#555;\'>No articles yet</p><p>Run the monitor to start collecting.</p></div>' if not articles else all_sections}
  </main>

</div>

<footer class="footer">
  <div class="built-by">Built by <span>Lou</span> · NewsWatch · GitHub Actions</div>
  <a href="feed.xml" style="color:#bbb;">Subscribe via RSS</a>
</footer>

</body>
</html>'''

    # Fix the source count expression in the dateline (can't use set comprehension in f-string easily)
    import re
    n_sources = len(set(
        (a.get('publisher') or {}).get('title', '') if isinstance(a.get('publisher'), dict)
        else str(a.get('publisher', ''))
        for a in news_articles
    ))
    html = html.replace(
        'len(set(a.get("publisher","") if isinstance(a.get("publisher"),"") else (a.get("publisher") or {{}}).get("title","") for a in news_articles))',
        str(n_sources)
    )

    out_path = os.path.join(DOCS_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[dashboard] {out_path} — {len(sapd_articles)} SAPD + {len(news_articles)} news, {len(topic_list)} topics")
