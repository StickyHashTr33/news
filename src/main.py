"""
main.py — NewsWatch orchestrator.

Flow:
  1. Load config/topics.yml + config/sources.yml
  2. Init SQLite DB
  3. Fetch ALL RSS feeds once, match articles to topics locally
  4. For each topic: dedup → alert → mark seen
  5. Generate RSS feed and dashboard from full DB history
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

CONFIG_PATH  = os.environ.get('CONFIG_PATH',  'config/topics.yml')
SOURCES_PATH = os.environ.get('SOURCES_PATH', 'config/sources.yml')


def load_topics(path: str) -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f).get('topics', [])


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

    # Fetch all feeds once and match across all topics
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

    print("\n── Generating dashboard and RSS ──")
    recent = get_recent(limit=300)
    stats  = get_stats()

    generate_rss(recent)
    generate_dashboard(recent, stats)

    print("\n" + "=" * 60)
    print(f"  Done. {len(all_new_articles)} new articles this run.")
    print(f"  DB total: {stats.get('total','?')} | Last 24h: {stats.get('last_24h','?')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
