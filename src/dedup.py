"""
dedup.py — SQLite-backed deduplication so each article only alerts once.
"""

import os
import sqlite3
import hashlib
from datetime import datetime

DB_PATH = os.environ.get('DB_PATH', 'data/seen.db')


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS seen_articles (
            url_hash    TEXT PRIMARY KEY,
            url         TEXT NOT NULL,
            title       TEXT,
            topic       TEXT,
            keyword     TEXT,
            publisher   TEXT,
            published   TEXT,
            description TEXT,
            seen_at     TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[dedup] DB ready at {DB_PATH}")


def _hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def is_new(url: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute('SELECT 1 FROM seen_articles WHERE url_hash = ?', (_hash(url),))
    exists = cur.fetchone() is not None
    conn.close()
    return not exists


def mark_seen(article: dict):
    publisher = article.get('publisher', {})
    publisher_name = publisher.get('title', '') if isinstance(publisher, dict) else str(publisher)

    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT OR IGNORE INTO seen_articles
        (url_hash, url, title, topic, keyword, publisher, published, description, seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        _hash(article.get('url', '')),
        article.get('url', ''),
        article.get('title', ''),
        article.get('topic', ''),
        article.get('keyword', ''),
        publisher_name,
        article.get('published date', ''),
        article.get('description', ''),
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def filter_new(articles: list[dict]) -> list[dict]:
    return [a for a in articles if is_new(a.get('url', ''))]


def get_recent(limit: int = 200) -> list[dict]:
    """Return recently-seen articles for dashboard/RSS generation."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        'SELECT * FROM seen_articles ORDER BY seen_at DESC LIMIT ?', (limit,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    stats = {}
    cur = conn.execute('SELECT COUNT(*) FROM seen_articles')
    stats['total'] = cur.fetchone()[0]
    cur = conn.execute(
        "SELECT COUNT(*) FROM seen_articles WHERE seen_at >= date('now','-1 day')"
    )
    stats['last_24h'] = cur.fetchone()[0]
    cur = conn.execute(
        'SELECT topic, COUNT(*) as cnt FROM seen_articles GROUP BY topic ORDER BY cnt DESC'
    )
    stats['by_topic'] = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return stats
