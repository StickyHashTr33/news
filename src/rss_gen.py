"""
rss_gen.py — Generates docs/feed.xml from recent articles (served via GitHub Pages).
"""

import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

DOCS_DIR = os.environ.get('DOCS_DIR', 'docs')
SITE_URL = os.environ.get('SITE_URL', 'https://YOUR_USERNAME.github.io/news-keyword-monitor')


def generate_rss(articles: list[dict]):
    os.makedirs(DOCS_DIR, exist_ok=True)

    rss = Element('rss')
    rss.set('version', '2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = 'NewsWatch'
    SubElement(channel, 'link').text = SITE_URL
    SubElement(channel, 'description').text = 'Keyword-monitored news feed'
    SubElement(channel, 'language').text = 'en-us'
    SubElement(channel, 'lastBuildDate').text = datetime.utcnow().strftime(
        '%a, %d %b %Y %H:%M:%S +0000'
    )

    atom_link = SubElement(channel, 'atom:link')
    atom_link.set('href', f'{SITE_URL}/feed.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    for a in articles[:100]:  # cap at 100 items
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = a.get('title', 'No title')
        SubElement(item, 'link').text = a.get('url', '')
        SubElement(item, 'guid').text = a.get('url', '')
        SubElement(item, 'description').text = (
            f"[{a.get('topic', '')}] Keyword: {a.get('keyword', '')} — "
            f"{a.get('description', '')}"
        )
        SubElement(item, 'category').text = a.get('topic', '')
        pub = a.get('published', a.get('published date', ''))
        if pub:
            SubElement(item, 'pubDate').text = pub

    xml_str = minidom.parseString(tostring(rss, encoding='unicode')).toprettyxml(indent='  ')
    # Remove the extra XML declaration minidom adds
    lines = xml_str.split('\n')
    clean = '\n'.join(lines[1:]) if lines[0].startswith('<?xml') else xml_str

    out_path = os.path.join(DOCS_DIR, 'feed.xml')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(clean)

    print(f"[rss] Generated {out_path} ({len(articles)} items)")
