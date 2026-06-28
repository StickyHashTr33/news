"""
scraper.py — Fetches RSS feeds from the curated sources allowlist,
then matches articles against each topic's keywords locally.
No Google. No aggregators. Only the outlets you approved.
"""

import os
import time
import yaml
import feedparser
import requests
from datetime import datetime, timezone

SOURCES_PATH = os.environ.get('SOURCES_PATH', 'config/sources.yml')
FETCH_TIMEOUT = 15   # seconds per feed
DELAY_BETWEEN_FEEDS = 0.5  # seconds — polite crawl rate


def load_sources(path: str = SOURCES_PATH) -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('sources', [])


def _fetch_feed(source: dict) -> list[dict]:
    """Fetch a single RSS/Atom feed and return normalized article dicts."""
    name = source['name']
    url = source['url']

    try:
        # feedparser can parse directly but using requests gives us better
        # timeout control and a real user-agent
        headers = {'User-Agent': 'NewsWatch/1.0 (RSS reader; open source)'}
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers=headers)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"  [feed] SKIP {name}: {e}")
        return []

    articles = []
    for entry in feed.entries:
        # Normalize across RSS and Atom formats
        pub = entry.get('published', entry.get('updated', ''))
        desc = entry.get('summary', entry.get('content', [{}])[0].get('value', ''))

        articles.append({
            'title':          entry.get('title', '').strip(),
            'url':            entry.get('link', '').strip(),
            'description':    _strip_html(desc)[:500],
            'published date': pub,
            'publisher':      {'title': name},
            'source_category': source.get('category', ''),
        })

    return articles


def _strip_html(text: str) -> str:
    """Very lightweight HTML tag stripper — avoids needing BeautifulSoup."""
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


def _matches(article: dict, keywords: list[str]) -> str | None:
    """
    Returns the first matching keyword if any keyword appears in the
    article title or description (case-insensitive). Otherwise None.
    """
    haystack = (
        (article.get('title') or '') + ' ' +
        (article.get('description') or '')
    ).lower()

    for kw in keywords:
        if kw.lower() in haystack:
            return kw
    return None


def fetch_all_topics(topics: list[dict]) -> dict[str, list[dict]]:
    """
    Fetches every source feed once, then matches articles across all topics.
    Returns a dict of {topic_name: [articles]}.
    """
    sources = load_sources()
    print(f"[scraper] {len(sources)} sources loaded")

    # Fetch every feed once (shared across all topics — efficient)
    all_articles: list[dict] = []
    for source in sources:
        print(f"  [feed] {source['name']}")
        articles = _fetch_feed(source)
        all_articles.extend(articles)
        time.sleep(DELAY_BETWEEN_FEEDS)

    print(f"[scraper] {len(all_articles)} total articles fetched across all feeds")

    # Match articles to topics
    results: dict[str, list[dict]] = {t['name']: [] for t in topics}
    seen_per_topic: dict[str, set] = {t['name']: set() for t in topics}

    for article in all_articles:
        url = article.get('url', '')
        if not url:
            continue
        for topic in topics:
            name = topic['name']
            kw = _matches(article, topic.get('keywords', []))
            if kw and url not in seen_per_topic[name]:
                seen_per_topic[name].add(url)
                tagged = dict(article)
                tagged['topic'] = name
                tagged['keyword'] = kw
                results[name].append(tagged)

    for topic_name, articles in results.items():
        print(f"  [match] '{topic_name}': {len(articles)} articles matched")

    return results
