"""
sapd_fetcher.py — Scrapes SAPD Calls for Service from the live city web page.

Source: https://webapp3.sanantonio.gov/policecalls/Calls.aspx
        (Non-Dispositioned Calls — actively being worked by officers)

No API key needed. Pure HTML table scraping with BeautifulSoup.
"""

import os
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

SAPD_CONFIG_PATH = os.environ.get('SAPD_CONFIG_PATH', 'config/sapd_config.yml')
CALLS_URL = 'https://webapp3.sanantonio.gov/policecalls/Calls.aspx'


def load_sapd_config(path: str = SAPD_CONFIG_PATH) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _matches_alert_types(problem_type: str, alert_on: list) -> bool:
    if not alert_on:
        return True
    p = problem_type.upper()
    return any(pattern.upper() in p for pattern in alert_on)


def _matches_division(division: str, watch_divisions: list) -> bool:
    if not watch_divisions:
        return True
    return division.upper() in [d.upper() for d in watch_divisions]


def _parse_calls_page(html: str) -> list[dict]:
    """Parse the SAPD calls HTML table into a list of call dicts."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='gvCalls') or soup.find('table', {'id': lambda x: x and 'Call' in x})

    if not table:
        # fallback: grab all tables and find the one with incident data
        tables = soup.find_all('table')
        for t in tables:
            if t.find('td', string=lambda s: s and 'SAPD-' in str(s)):
                table = t
                break

    if not table:
        print("[sapd] Could not find calls table in HTML")
        return []

    calls = []
    rows = table.find_all('tr')

    for row in rows[1:]:  # skip header row
        cols = row.find_all('td')
        if len(cols) < 5:
            continue

        # Column order: Map | Incident Number | DateTime | Problem Type | Address | Division
        try:
            incident = cols[1].get_text(strip=True)
            if not incident.startswith('SAPD-'):
                continue
            dt_str     = cols[2].get_text(strip=True)
            problem    = cols[3].get_text(strip=True)
            address    = cols[4].get_text(strip=True)
            division   = cols[5].get_text(strip=True) if len(cols) > 5 else ''

            calls.append({
                'incident_number': incident,
                'dt_str':          dt_str,
                'problem':         problem,
                'address':         address,
                'division':        division,
            })
        except (IndexError, AttributeError):
            continue

    return calls


def _normalize(record: dict) -> dict:
    """Convert a parsed call dict to the standard article dict format."""
    incident = record['incident_number']
    problem  = record['problem']
    address  = record['address']
    division = record['division']
    dt_str   = record['dt_str']

    # Link to Google Maps for the address — no individual incident page exists
    maps_query = (address + ' San Antonio TX').replace(' ', '+')
    url = f"https://maps.google.com/maps?q={maps_query}"
    # Use incident number as dedup key in a stable synthetic URI
    dedup_url = f"https://webapp3.sanantonio.gov/policecalls/Calls.aspx#{incident}"
    title = f"[SAPD] {problem} — {address} ({division})"
    desc  = f"Incident #{incident} | {division} Division | {dt_str}"

    return {
        'title':           title,
        'url':             dedup_url,
        'maps_url':        url,
        'description':     desc,
        'published date':  dt_str,
        'publisher':       {'title': 'SAPD Calls for Service'},
        'topic':           'SAPD Calls for Service',
        'keyword':         problem,
        'incident_number': incident,
        'call_type':       problem,
        'address':         address,
        'division':        division,
        'is_sapd':         True,
    }


def fetch_sapd_calls() -> list[dict]:
    """
    Fetch active SAPD calls, filter by configured types and divisions.
    Returns normalized call dicts ready for dedup + alerting.
    """
    cfg          = load_sapd_config()
    alert_on     = cfg.get('alert_on', [])
    watch_divs   = cfg.get('watch_divisions', [])

    print(f"[sapd] Fetching: {CALLS_URL}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsWatch/1.0)'}
        resp = requests.get(CALLS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[sapd] Fetch error: {e}")
        return []

    raw_calls = _parse_calls_page(resp.text)
    print(f"[sapd] {len(raw_calls)} total active calls on page")

    matched = []
    for call in raw_calls:
        if (_matches_alert_types(call['problem'], alert_on) and
                _matches_division(call['division'], watch_divs)):
            matched.append(_normalize(call))

    print(f"[sapd] {len(matched)} calls matched alert filters")
    return matched


def build_sapd_discord_payload(calls: list[dict]) -> list[dict]:
    """Build Discord embeds for SAPD calls."""
    from collections import Counter

    if not calls:
        return []

    type_counts = Counter(c['call_type'] for c in calls)
    summary = ' | '.join(f"{t}: {n}" for t, n in type_counts.most_common(5))

    PRIORITY_COLORS = {
        'SHOOTING':        0xef4444,
        'SHOTS FIRED':     0xef4444,
        'HOMICIDE':        0xef4444,
        'ACTIVE SHOOTER':  0xef4444,
        'ASSAULT':         0xf97316,
        'ROBBERY':         0xf97316,
        'SEXUAL ASSAULT':  0xf97316,
        'STABBING':        0xf97316,
        'OVERDOSE':        0xeab308,
        'MISSING PERSON':  0xeab308,
    }

    embeds = []
    for call in calls[:10]:
        ctype = call.get('call_type', '').upper()
        color = next(
            (v for k, v in PRIORITY_COLORS.items() if k in ctype),
            0xf59e0b
        )
        embeds.append({
            "title":       call['title'][:256],
            "url":         call.get('maps_url', ''),
            "description": call['description'][:400] + "\n[View on map](" + call.get('maps_url','') + ")",
            "color":       color,
            "footer":      {"text": call.get('published date', '')},
        })

    return [{
        "username": "NewsWatch — SAPD",
        "content":  f"🚨 **SAPD Active Calls** — {len(calls)} alert(s)\n`{summary}`",
        "embeds":   embeds,
    }]
