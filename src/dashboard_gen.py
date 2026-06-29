"""
dashboard_gen.py — Generates docs/index.html: a dark terminal-aesthetic news dashboard.
Served via GitHub Pages.
"""

import os
import json
from datetime import datetime
from collections import defaultdict

DOCS_DIR = os.environ.get('DOCS_DIR', 'docs')
SITE_URL = os.environ.get('SITE_URL', 'https://YOUR_USERNAME.github.io/news-keyword-monitor')


def _ticker_items(articles: list[dict]) -> str:
    items = articles[:30]
    return ''.join(
        f'<span class="tick-item"><span class="tick-topic">[{a.get("topic", "")}]</span>'
        f'<a href="{a.get("url", "")}" target="_blank" rel="noopener">'
        f'{a.get("title", "")}</a></span>'
        for a in items
    )


def _article_card(a: dict) -> str:
    publisher = a.get('publisher', '')
    pub_date = a.get('published', a.get('published date', ''))
    keyword = a.get('keyword', '')
    desc = (a.get('description') or '')[:180]

    return f'''
    <article class="card">
      <a class="card-title" href="{a.get('url', '')}" target="_blank" rel="noopener">
        {a.get('title', 'No title')}
      </a>
      <p class="card-desc">{desc}</p>
      <div class="card-meta">
        <span class="kw-badge">{keyword}</span>
        {f'<span class="publisher">{publisher}</span>' if publisher else ''}
        {f'<span class="pub-date">{pub_date}</span>' if pub_date else ''}
      </div>
    </article>'''


def generate_dashboard(articles: list[dict], stats: dict = None):
    os.makedirs(DOCS_DIR, exist_ok=True)

    # Group by topic
    by_topic = defaultdict(list)
    for a in articles:
        by_topic[a.get('topic', 'Uncategorized')].append(a)

    # Build topic sections
    topic_nav = ''.join(
        f'<a class="nav-topic" href="#topic-{i}">{topic}</a>'
        for i, topic in enumerate(by_topic)
    )

    topic_sections = ''
    for i, (topic, items) in enumerate(by_topic.items()):
        cards = ''.join(_article_card(a) for a in items[:50])
        topic_sections += f'''
        <section class="topic-section" id="topic-{i}">
          <div class="topic-header">
            <h2 class="topic-title">{topic}</h2>
            <span class="topic-count">{len(items)} article{"s" if len(items) != 1 else ""}</span>
          </div>
          <div class="card-grid">{cards}</div>
        </section>'''

    total = stats.get('total', len(articles)) if stats else len(articles)
    last_24h = stats.get('last_24h', '—') if stats else '—'
    updated = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    ticker = _ticker_items(articles)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NewsWatch</title>
  <link rel="alternate" type="application/rss+xml" title="NewsWatch Feed" href="feed.xml">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:        #0a0a0a;
      --surface:   #111111;
      --surface2:  #171717;
      --border:    #222222;
      --text:      #e2e2e2;
      --muted:     #666666;
      --amber:     #f59e0b;
      --amber-dim: #92600a;
      --red:       #ef4444;
      --green:     #22c55e;
    }}

    html {{ scroll-behavior: smooth; }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      min-height: 100vh;
    }}

    /* ── Ticker ── */
    .ticker-wrap {{
      background: #000;
      border-bottom: 1px solid var(--amber-dim);
      overflow: hidden;
      white-space: nowrap;
      padding: 0;
      height: 36px;
      display: flex;
      align-items: center;
    }}
    .ticker-label {{
      background: var(--amber);
      color: #000;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      padding: 0 14px;
      height: 100%;
      display: flex;
      align-items: center;
      flex-shrink: 0;
      z-index: 1;
    }}
    .ticker-track {{
      display: inline-flex;
      gap: 0;
      animation: ticker 180s linear infinite;
    }}
    .tick-item {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0 28px;
      border-right: 1px solid #222;
      font-size: 12px;
      color: var(--muted);
    }}
    .tick-item a {{
      color: var(--text);
      text-decoration: none;
      font-size: 12px;
    }}
    .tick-item a:hover {{ color: var(--amber); }}
    .tick-topic {{
      color: var(--amber);
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 500;
    }}
    @keyframes ticker {{
      0%   {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}

    /* ── Header ── */
    .site-header {{
      border-bottom: 1px solid var(--border);
      padding: 20px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .wordmark {{
      display: flex;
      align-items: baseline;
      gap: 10px;
    }}
    .wordmark-title {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 28px;
      font-weight: 900;
      color: var(--text);
      letter-spacing: -0.5px;
    }}
    .wordmark-title span {{
      color: var(--amber);
    }}
    .wordmark-sub {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: var(--muted);
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
    .header-meta {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .stat-pill {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }}
    .stat-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 18px;
      font-weight: 500;
      color: var(--amber);
    }}
    .stat-lbl {{
      font-size: 10px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .header-links {{
      display: flex;
      gap: 12px;
    }}
    .header-links a {{
      color: var(--muted);
      text-decoration: none;
      font-size: 12px;
      padding: 6px 12px;
      border: 1px solid var(--border);
      border-radius: 4px;
      transition: all 0.15s;
    }}
    .header-links a:hover {{
      color: var(--amber);
      border-color: var(--amber);
    }}

    /* ── Updated bar ── */
    .updated-bar {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 8px 32px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--muted);
      display: flex;
      gap: 24px;
      align-items: center;
    }}
    .updated-bar .pulse {{
      width: 7px; height: 7px;
      background: var(--green);
      border-radius: 50%;
      display: inline-block;
      animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.3; }}
    }}

    /* ── Layout ── */
    .layout {{
      display: flex;
      min-height: calc(100vh - 160px);
    }}
    .sidebar {{
      width: 200px;
      flex-shrink: 0;
      border-right: 1px solid var(--border);
      padding: 24px 0;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
    }}
    .sidebar-label {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 9px;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: var(--muted);
      padding: 0 20px;
      margin-bottom: 12px;
    }}
    .nav-topic {{
      display: block;
      padding: 10px 20px;
      color: var(--muted);
      text-decoration: none;
      font-size: 13px;
      border-left: 2px solid transparent;
      transition: all 0.15s;
    }}
    .nav-topic:hover {{
      color: var(--text);
      border-left-color: var(--amber);
      background: var(--surface);
    }}
    .main-content {{
      flex: 1;
      overflow-y: auto;
      padding: 32px;
    }}

    /* ── Topic sections ── */
    .topic-section {{
      margin-bottom: 48px;
    }}
    .topic-header {{
      display: flex;
      align-items: baseline;
      gap: 14px;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }}
    .topic-title {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 20px;
      font-weight: 700;
      color: var(--text);
    }}
    .topic-count {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--muted);
    }}

    /* ── Cards ── */
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      transition: border-color 0.15s, background 0.15s;
    }}
    .card:hover {{
      border-color: var(--amber-dim);
      background: var(--surface2);
    }}
    .card-title {{
      display: block;
      font-size: 14px;
      font-weight: 600;
      line-height: 1.45;
      color: var(--text);
      text-decoration: none;
      margin-bottom: 8px;
    }}
    .card-title:hover {{ color: var(--amber); }}
    .card-desc {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 12px;
    }}
    .card-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .kw-badge {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      background: #1a1400;
      color: var(--amber);
      border: 1px solid var(--amber-dim);
      padding: 2px 7px;
      border-radius: 3px;
    }}
    .publisher {{
      font-size: 11px;
      color: var(--muted);
    }}
    .pub-date {{
      font-size: 10px;
      color: #444;
      font-family: 'JetBrains Mono', monospace;
      margin-left: auto;
    }}

    /* ── Empty state ── */
    .empty {{
      text-align: center;
      padding: 80px 20px;
      color: var(--muted);
    }}
    .empty h3 {{
      font-family: 'Playfair Display', serif;
      font-size: 20px;
      margin-bottom: 8px;
      color: var(--text);
    }}

    /* ── Responsive ── */
    @media (max-width: 700px) {{
      .sidebar {{ display: none; }}
      .site-header {{ padding: 16px; }}
      .main-content {{ padding: 16px; }}
      .card-grid {{ grid-template-columns: 1fr; }}
      .header-meta {{ display: none; }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      .ticker-track {{ animation: none; }}
      .pulse {{ animation: none; }}
    }}
  </style>
</head>
<body>

  <!-- Ticker -->
  <div class="ticker-wrap">
    <div class="ticker-label">Live</div>
    <div style="overflow:hidden;flex:1;">
      <div class="ticker-track">
        {ticker}{ticker}
      </div>
    </div>
  </div>

  <!-- Header -->
  <header class="site-header">
    <div class="wordmark">
      <span class="wordmark-title">News<span>Watch</span></span>
      <span class="wordmark-sub">Keyword Monitor</span>
    </div>
    <div class="header-meta">
      <div class="stat-pill">
        <span class="stat-val">{total}</span>
        <span class="stat-lbl">Total Articles</span>
      </div>
      <div class="stat-pill">
        <span class="stat-val">{last_24h}</span>
        <span class="stat-lbl">Last 24h</span>
      </div>
      <div class="header-links">
        <a href="feed.xml">RSS Feed</a>
        <a href="https://github.com" target="_blank">GitHub</a>
      </div>
    </div>
  </header>

  <!-- Updated bar -->
  <div class="updated-bar">
    <span class="pulse"></span>
    <span>Last updated: {updated}</span>
    <span>·</span>
    <span>{len(by_topic)} topic(s) monitored</span>
  </div>

  <!-- Main layout -->
  <div class="layout">
    <nav class="sidebar">
      <div class="sidebar-label">Topics</div>
      {topic_nav}
    </nav>
    <main class="main-content">
      {'<div class="empty"><h3>No articles yet</h3><p>Run the monitor to start collecting.</p></div>' if not articles else topic_sections}
    </main>
  </div>

</body>
</html>'''

    out_path = os.path.join(DOCS_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[dashboard] Generated {out_path} ({len(articles)} articles, {len(by_topic)} topics)")
