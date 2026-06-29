"""
dashboard_gen.py — Generates docs/index.html
Editorial press aesthetic: warm white, serif masthead, color-coded topics.
"""

import os
from datetime import datetime
from collections import defaultdict

DOCS_DIR = os.environ.get('DOCS_DIR', 'docs')
SITE_URL  = os.environ.get('SITE_URL', 'https://YOUR_USERNAME.github.io/news-keyword-monitor')

# ── Topic color palette ────────────────────────────────────────────────────
# Each topic gets a color based on its name. Colors cycle from this list.
TOPIC_COLORS = [
    {"bg": "#E1F5EE", "text": "#0F6E56", "border": "#5DCAA5", "pill": "#0F6E56"},  # teal
    {"bg": "#E6F1FB", "text": "#185FA5", "border": "#85B7EB", "pill": "#185FA5"},  # blue
    {"bg": "#EEEDFE", "text": "#534AB7", "border": "#AFA9EC", "pill": "#534AB7"},  # purple
    {"bg": "#FAEEDA", "text": "#854F0B", "border": "#EF9F27", "pill": "#854F0B"},  # amber
    {"bg": "#EAF3DE", "text": "#3B6D11", "border": "#97C459", "pill": "#3B6D11"},  # green
    {"bg": "#FAECE7", "text": "#993C1D", "border": "#F0997B", "pill": "#993C1D"},  # coral
    {"bg": "#FBEAF0", "text": "#993556", "border": "#ED93B1", "pill": "#993556"},  # pink
    {"bg": "#FCEBEB", "text": "#A32D2D", "border": "#F09595", "pill": "#A32D2D"},  # red
]


def _topic_color(topic_name: str, index: int) -> dict:
    return TOPIC_COLORS[index % len(TOPIC_COLORS)]


def _time_ago(dt_str: str) -> str:
    """Convert ISO timestamp to human-readable relative time."""
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
    seen_at   = a.get('seen_at', '')
    timeago   = _time_ago(seen_at)

    return f'''
    <article class="card" style="border-left: 3px solid {color['border']};">
      <a class="card-title" href="{url}" target="_blank" rel="noopener">{title}</a>
      {f'<p class="card-desc">{desc}</p>' if desc else ''}
      <div class="card-meta">
        {f'<span class="kw-pill" style="background:{color["bg"]};color:{color["text"]};">{keyword}</span>' if keyword else ''}
        {f'<span class="publisher">{publisher}</span>' if publisher else ''}
        {f'<span class="timeago">{timeago}</span>' if timeago else ''}
      </div>
    </article>'''


def _wire_item(a: dict, color: dict) -> str:
    title   = (a.get('title') or 'Untitled')[:90]
    url     = a.get('url', '#')
    topic   = a.get('topic', '')
    seen_at = a.get('seen_at', '')
    timeago = _time_ago(seen_at)
    return f'''
      <li class="wire-item">
        <span class="wire-dot" style="background:{color['border']};"></span>
        <div class="wire-body">
          <a href="{url}" target="_blank" rel="noopener" class="wire-title">{title}</a>
          <div class="wire-meta">
            <span class="wire-topic" style="color:{color['text']};">{topic}</span>
            {f'<span class="wire-time">{timeago}</span>' if timeago else ''}
          </div>
        </div>
      </li>'''


def generate_dashboard(articles: list[dict], stats: dict = None):
    os.makedirs(DOCS_DIR, exist_ok=True)

    by_topic = defaultdict(list)
    for a in articles:
        by_topic[a.get('topic', 'Other')].append(a)

    topic_list  = list(by_topic.keys())
    topic_color_map = {t: _topic_color(t, i) for i, t in enumerate(topic_list)}

    # Nav pills
    nav_pills = ''.join(
        f'<a class="nav-pill" href="#topic-{i}" '
        f'style="background:{topic_color_map[t]["bg"]};color:{topic_color_map[t]["text"]};">'
        f'{t}</a>'
        for i, t in enumerate(topic_list)
    )

    # Topic sections
    sections = ''
    for i, (topic, items) in enumerate(by_topic.items()):
        color = topic_color_map[topic]
        cards = ''.join(_article_card(a, color) for a in items[:30])
        sections += f'''
        <section class="topic-section" id="topic-{i}">
          <div class="topic-header" style="border-bottom: 2px solid {color['border']};">
            <h2 class="topic-name" style="color:{color['text']};">{topic}</h2>
            <span class="topic-count">{len(items)} article{"s" if len(items)!=1 else ""}</span>
          </div>
          <div class="card-grid">{cards}</div>
        </section>'''

    # Wire feed (20 most recent across all topics)
    wire_items = ''.join(
        _wire_item(a, topic_color_map.get(a.get('topic',''), TOPIC_COLORS[0]))
        for a in articles[:20]
    )

    # Ticker
    ticker_items = ''.join(
        f'<span class="tick-item">'
        f'<span class="tick-topic" style="color:{topic_color_map.get(a.get("topic",""), TOPIC_COLORS[0])["border"]};">'
        f'{a.get("topic","")}</span>'
        f'<a href="{a.get("url","")}" target="_blank" rel="noopener">{(a.get("title") or "")[:80]}</a>'
        f'</span>'
        for a in articles[:25]
    )

    total   = stats.get('total', len(articles)) if stats else len(articles)
    last24h = stats.get('last_24h', '—') if stats else '—'
    updated = datetime.utcnow().strftime('%B %d, %Y · %H:%M UTC')
    n_sources = len(set(
        (a.get('publisher') or {}).get('title','') if isinstance(a.get('publisher'), dict)
        else str(a.get('publisher',''))
        for a in articles
    ))

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
    body{{
      background:#FAFAF8;
      color:#1a1a18;
      font-family:'Inter',system-ui,sans-serif;
      font-size:14px;
      line-height:1.6;
    }}
    a{{color:inherit;text-decoration:none}}
    a:hover{{text-decoration:underline}}

    /* ── Ticker ── */
    .ticker-wrap{{
      background:#111;
      overflow:hidden;
      white-space:nowrap;
      height:34px;
      display:flex;
      align-items:center;
    }}
    .ticker-label{{
      background:#c0392b;
      color:#fff;
      font-family:'JetBrains Mono',monospace;
      font-size:9px;
      font-weight:400;
      letter-spacing:2px;
      text-transform:uppercase;
      padding:0 12px;
      height:100%;
      display:flex;
      align-items:center;
      flex-shrink:0;
    }}
    .ticker-track{{
      display:inline-flex;
      animation:ticker 180s linear infinite;
    }}
    .tick-item{{
      display:inline-flex;
      align-items:center;
      gap:10px;
      padding:0 24px;
      border-right:1px solid #2a2a2a;
      font-size:12px;
      color:#888;
    }}
    .tick-item a{{color:#ddd;font-size:12px}}
    .tick-item a:hover{{color:#fff;text-decoration:none}}
    .tick-topic{{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1px;text-transform:uppercase}}
    @keyframes ticker{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}

    /* ── Masthead ── */
    .masthead{{
      border-bottom:2px solid #1a1a18;
      padding:20px 32px 16px;
    }}
    .masthead-inner{{
      display:flex;
      align-items:flex-end;
      justify-content:space-between;
      flex-wrap:wrap;
      gap:12px;
    }}
    .masthead-left{{display:flex;align-items:baseline;gap:16px}}
    .wordmark{{
      font-family:'Playfair Display',Georgia,serif;
      font-size:36px;
      font-weight:900;
      letter-spacing:-1px;
      line-height:1;
      color:#1a1a18;
    }}
    .wordmark em{{font-style:normal;color:#c0392b}}
    .masthead-tagline{{
      font-size:11px;
      color:#999;
      font-family:'JetBrains Mono',monospace;
      letter-spacing:1px;
      text-transform:uppercase;
    }}
    .masthead-right{{
      display:flex;
      align-items:center;
      gap:28px;
    }}
    .stat-block{{text-align:right}}
    .stat-num{{
      font-family:'Playfair Display',serif;
      font-size:22px;
      font-weight:700;
      color:#1a1a18;
      line-height:1;
    }}
    .stat-lbl{{
      font-size:10px;
      color:#999;
      text-transform:uppercase;
      letter-spacing:1px;
      font-family:'JetBrains Mono',monospace;
    }}
    .masthead-links{{display:flex;gap:10px;align-items:center}}
    .masthead-links a{{
      font-size:12px;
      color:#555;
      border:1px solid #ddd;
      padding:5px 12px;
      border-radius:4px;
      font-family:'Inter',sans-serif;
    }}
    .masthead-links a:hover{{border-color:#1a1a18;color:#1a1a18;text-decoration:none}}

    /* ── Dateline ── */
    .dateline{{
      padding:8px 32px;
      border-bottom:1px solid #E8E5DF;
      font-family:'JetBrains Mono',monospace;
      font-size:11px;
      color:#999;
      display:flex;
      align-items:center;
      gap:6px;
      background:#FAFAF8;
    }}
    .live-dot{{
      width:6px;height:6px;
      background:#2ecc71;
      border-radius:50%;
      display:inline-block;
      animation:pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}

    /* ── Topic nav ── */
    .topic-nav{{
      padding:12px 32px;
      border-bottom:1px solid #E8E5DF;
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      background:#fff;
      position:sticky;
      top:0;
      z-index:10;
    }}
    .nav-pill{{
      font-size:11px;
      font-weight:500;
      padding:4px 10px;
      border-radius:20px;
      white-space:nowrap;
      font-family:'Inter',sans-serif;
    }}
    .nav-pill:hover{{opacity:0.8;text-decoration:none}}

    /* ── Layout ── */
    .layout{{
      display:grid;
      grid-template-columns:1fr 280px;
      min-height:calc(100vh - 160px);
      gap:0;
    }}
    .main-col{{
      border-right:1px solid #E8E5DF;
      padding:28px 32px;
    }}
    .sidebar-col{{
      padding:20px;
      position:sticky;
      top:52px;
      height:calc(100vh - 52px);
      overflow-y:auto;
    }}

    /* ── Topic sections ── */
    .topic-section{{margin-bottom:44px}}
    .topic-header{{
      display:flex;
      align-items:baseline;
      justify-content:space-between;
      padding-bottom:10px;
      margin-bottom:16px;
    }}
    .topic-name{{
      font-family:'Playfair Display',Georgia,serif;
      font-size:20px;
      font-weight:700;
    }}
    .topic-count{{
      font-family:'JetBrains Mono',monospace;
      font-size:10px;
      color:#aaa;
      letter-spacing:1px;
    }}
    .card-grid{{
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
      gap:12px;
    }}

    /* ── Article cards ── */
    .card{{
      background:#fff;
      border:1px solid #E8E5DF;
      border-radius:6px;
      padding:14px 14px 12px 16px;
      transition:border-color 0.15s;
    }}
    .card:hover{{border-color:#bbb}}
    .card-title{{
      display:block;
      font-size:13px;
      font-weight:500;
      line-height:1.45;
      color:#1a1a18;
      margin-bottom:6px;
    }}
    .card-title:hover{{color:#333;text-decoration:underline}}
    .card-desc{{
      font-size:12px;
      color:#888;
      line-height:1.5;
      margin-bottom:10px;
    }}
    .card-meta{{
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      align-items:center;
    }}
    .kw-pill{{
      font-size:10px;
      font-family:'JetBrains Mono',monospace;
      padding:2px 7px;
      border-radius:3px;
      font-weight:400;
    }}
    .publisher{{font-size:11px;color:#aaa}}
    .timeago{{font-size:10px;color:#ccc;margin-left:auto;font-family:'JetBrains Mono',monospace}}

    /* ── Wire sidebar ── */
    .wire-header{{
      font-family:'Playfair Display',Georgia,serif;
      font-size:14px;
      font-weight:700;
      color:#1a1a18;
      text-transform:uppercase;
      letter-spacing:2px;
      padding-bottom:10px;
      border-bottom:2px solid #1a1a18;
      margin-bottom:14px;
    }}
    .wire-list{{list-style:none}}
    .wire-item{{
      display:flex;
      gap:10px;
      padding:10px 0;
      border-bottom:1px solid #F0EDE8;
    }}
    .wire-dot{{
      width:6px;height:6px;
      border-radius:50%;
      flex-shrink:0;
      margin-top:5px;
    }}
    .wire-body{{flex:1;min-width:0}}
    .wire-title{{
      display:block;
      font-size:12px;
      font-weight:500;
      color:#1a1a18;
      line-height:1.4;
      margin-bottom:3px;
    }}
    .wire-title:hover{{text-decoration:underline}}
    .wire-meta{{display:flex;justify-content:space-between;align-items:center}}
    .wire-topic{{font-size:10px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:0.5px}}
    .wire-time{{font-size:10px;color:#ccc;font-family:'JetBrains Mono',monospace}}

    /* ── Empty state ── */
    .empty{{
      grid-column:1/-1;
      text-align:center;
      padding:80px 20px;
      color:#aaa;
    }}
    .empty h3{{
      font-family:'Playfair Display',serif;
      font-size:22px;
      color:#555;
      margin-bottom:8px;
    }}

    /* ── Footer ── */
    .footer{{
      border-top:1px solid #E8E5DF;
      padding:16px 32px;
      font-size:11px;
      color:#bbb;
      font-family:'JetBrains Mono',monospace;
      display:flex;
      justify-content:space-between;
      align-items:center;
    }}

    /* ── Responsive ── */
    @media(max-width:768px){{
      .layout{{grid-template-columns:1fr}}
      .sidebar-col{{display:none}}
      .masthead{{padding:16px}}
      .main-col{{padding:16px}}
      .topic-nav{{padding:10px 16px}}
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
  <div class="ticker-label">Wire</div>
  <div style="overflow:hidden;flex:1;">
    <div class="ticker-track">{ticker_items}{ticker_items}</div>
  </div>
</div>

<header class="masthead">
  <div class="masthead-inner">
    <div class="masthead-left">
      <div class="wordmark">News<em>Watch</em></div>
      <div class="masthead-tagline">Independent news intelligence</div>
    </div>
    <div class="masthead-right">
      <div class="stat-block">
        <div class="stat-num">{total}</div>
        <div class="stat-lbl">Articles</div>
      </div>
      <div class="stat-block">
        <div class="stat-num">{last24h}</div>
        <div class="stat-lbl">Last 24h</div>
      </div>
      <div class="stat-block">
        <div class="stat-num">{n_sources}</div>
        <div class="stat-lbl">Sources</div>
      </div>
      <div class="masthead-links">
        <a href="feed.xml">RSS</a>
        <a href="https://github.com/StickyHashTr33/news" target="_blank" rel="noopener">GitHub</a>
      </div>
    </div>
  </div>
</header>

<div class="dateline">
  <span class="live-dot"></span>
  <span>Updated {updated}</span>
  <span style="color:#ddd">·</span>
  <span>{len(topic_list)} topics monitored</span>
</div>

<nav class="topic-nav" aria-label="Topics">
  {nav_pills}
</nav>

<div class="layout">
  <main class="main-col">
    {''.join(['<div class="empty"><h3>No articles yet</h3><p>Run the monitor to start collecting.</p></div>' if not articles else sections])}
  </main>

  <aside class="sidebar-col">
    <div class="wire-header">Latest wire</div>
    <ul class="wire-list">
      {wire_items if wire_items else '<li style="color:#aaa;font-size:12px;padding:10px 0">Nothing yet</li>'}
    </ul>
  </aside>
</div>

<footer class="footer">
  <span>NewsWatch · Auto-generated by GitHub Actions</span>
  <a href="feed.xml" style="color:#bbb;">Subscribe via RSS</a>
</footer>

</body>
</html>'''

    out_path = os.path.join(DOCS_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[dashboard] Generated {out_path} ({len(articles)} articles, {len(topic_list)} topics)")
