"""
main.py — NewsWatch orchestrator.

Flow:
  1. Load config/topics.yml + config/sources.yml
  2. Init SQLite DB
  3. Fetch ALL RSS feeds once, match articles to topics locally
  4. Fetch SAPD calls for service (if enabled)
  5. For each topic: dedup → alert → mark seen
  6. Generate RSS feed and dashboard from full DB history
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import yaml
from scraper import fetch_all_topics
from dedup import init_db, filter_new, mark_seen, get_recent, get_stats
from alerts import send_discord, send_email
from rss_gen import generate_rss
from dashboard_gen import generate_dashboard

CONFIG_PATH       = os.environ.get('CONFIG_PATH',       'config/topics.yml')
SOURCES_PATH      = os.environ.get('SOURCES_PATH',      'config/sources.yml')
SAPD_CONFIG_PATH  = os.environ.get('SAPD_CONFIG_PATH',  'config/sapd_config.yml')
ENABLE_SAPD       = os.environ.get('ENABLE_SAPD', 'true').lower() == 'true'


def load_topics(path: str) -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f).get('topics', [])


def run_sapd_module():
    """Fetch SAPD calls, dedup, alert, and mark seen. Returns new calls."""
    if not os.path.exists(SAPD_CONFIG_PATH):
        print("[sapd] Config not found — skipping SAPD module")
        return []

    try:
        import yaml as _yaml
        with open(SAPD_CONFIG_PATH) as f:
            sapd_cfg = _yaml.safe_load(f)
    except Exception as e:
        print(f"[sapd] Config load error: {e}")
        return []

    from sapd_fetcher import fetch_sapd_calls, build_sapd_discord_payload
    import requests as _requests

    calls = fetch_sapd_calls()
    new_calls = filter_new(calls)

    print(f"[sapd] {len(calls)} fetched | {len(new_calls)} new")

    if not new_calls:
        return []

    for call in new_calls:
        mark_seen(call)

    outputs = sapd_cfg.get('outputs', {})

    if outputs.get('discord'):
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if webhook_url:
            payloads = build_sapd_discord_payload(new_calls)
            for payload in payloads:
                try:
                    r = _requests.post(webhook_url, json=payload, timeout=15)
                    r.raise_for_status()
                    print(f"[sapd] Discord alert sent for {len(new_calls)} calls")
                except Exception as e:
                    print(f"[sapd] Discord error: {e}")
        else:
            print("[sapd] DISCORD_WEBHOOK_URL not set — skipping Discord")

    return new_calls


def main():
    print("=" * 60)
    print("  NewsWatch — starting run")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    topics = load_topics(CONFIG_PATH)
    if not topics:
        print("[main] No topics defined. Exiting.")
        sys.exit(0)

    init_db()

    # ── RSS module ────────────────────────────────────────────────────────
    matched = fetch_all_topics(topics)
    all_new_articles = []

    for topic in topics:
        name = topic['name']
        articles = matched.get(name, [])
        new_articles = filter_new(articles)

        print(f"\n── {name}: {len(articles)} matched | {len(new_articles)} new")

        if not new_articles:
            continue

        for a in new_articles:
            mark_seen(a)

        outputs = topic.get('outputs', {})
        if outputs.get('discord'):
            send_discord(new_articles, name)
        if outputs.get('email'):
            send_email(new_articles, name)

        all_new_articles.extend(new_articles)

    # ── SAPD module ───────────────────────────────────────────────────────
    sapd_calls = []
    if ENABLE_SAPD:
        print("\n── SAPD Calls for Service ──")
        sapd_calls = run_sapd_module()
        all_new_articles.extend(sapd_calls)

    # ── Generate dashboard and RSS ────────────────────────────────────────
    print("\n── Generating dashboard and RSS ──")
    recent = get_recent(limit=400)
    stats  = get_stats()

    generate_rss(recent)
    generate_dashboard(recent, stats)

    print("\n" + "=" * 60)
    print(f"  Done. {len(all_new_articles)} new items this run.")
    if sapd_calls:
        print(f"  SAPD: {len(sapd_calls)} new calls")
    print(f"  DB total: {stats.get('total','?')} | Last 24h: {stats.get('last_24h','?')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
