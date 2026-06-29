"""
sapd_fetcher.py — Polls the SAPD Calls for Service dataset via the
Socrata SODA API (data.sanantonio.gov) and returns new calls that
match configured alert types and priority filters.

Integrates with the same dedup/alert/dashboard pipeline as the RSS module.
"""

import os
import yaml
import requests
from datetime import datetime, timezone, timedelta


SAPD_CONFIG_PATH = os.environ.get('SAPD_CONFIG_PATH', 'config/sapd_config.yml')


def load_sapd_config(path: str = SAPD_CONFIG_PATH) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _build_query(cfg: dict) -> dict:
    """Build Socrata SODA query parameters."""
    f = cfg['fields']
    lookback = cfg['api'].get('lookback_hours', 13)
    since = (datetime.now(timezone.utc) - timedelta(hours=lookback)).strftime('%Y-%m-%dT%H:%M:%S')

    # Base time filter
    where_clauses = [f"{f['date_time']} >= '{since}'"]

    # District filter
    districts = cfg.get('watch_districts', [])
    if districts:
        dist_list = ', '.join(f"'{d}'" for d in districts)
        where_clauses.append(f"{f['district']} IN ({dist_list})")

    # Priority filter
    min_p = cfg.get('min_priority')
    max_p = cfg.get('max_priority')
    if min_p is not None:
        where_clauses.append(f"{f['priority']} >= '{min_p}'")
    if max_p is not None:
        where_clauses.append(f"{f['priority']} <= '{max_p}'")

    return {
        '$where': ' AND '.join(where_clauses),
        '$limit': cfg['api'].get('limit', 500),
        '$order': f"{f['date_time']} DESC",
    }


def _matches_alert_types(call_type: str, alert_on: list[str]) -> bool:
    """Returns True if this call type matches any configured alert pattern."""
    if not alert_on:
        return True  # empty list = alert on everything
    call_upper = call_type.upper()
    return any(pattern.upper() in call_upper for pattern in alert_on)


def _normalize(record: dict, cfg: dict) -> dict:
    """Normalize a Socrata record into the standard article dict format."""
    f = cfg['fields']

    incident  = record.get(f['incident_number'], 'UNKNOWN')
    call_type = record.get(f['call_type'], 'UNKNOWN')
    address   = record.get(f['address'], 'Unknown location')
    district  = record.get(f['district'], '?')
    priority  = record.get(f['priority'], '?')
    dt_raw    = record.get(f['date_time'], '')
    dispo     = record.get(f['disposition'], '')
    council   = record.get(f['council_district'], '')

    # Build a synthetic "URL" using incident number for dedup purposes
    url = f"https://data.sanantonio.gov/sapd/incident/{incident}"

    title = f"[SAPD] {call_type} — {address} (District {district})"
    description = (
        f"Incident #{incident} | Priority {priority} | "
        f"Council District {council} | Disposition: {dispo or 'Pending'} | "
        f"Time: {dt_raw}"
    )

    return {
        'title':          title,
        'url':            url,
        'description':    description,
        'published date': dt_raw,
        'publisher':      {'title': 'SAPD Calls for Service'},
        'topic':          'SAPD Calls for Service',
        'keyword':        call_type,
        'incident_number': incident,
        'call_type':      call_type,
        'address':        address,
        'district':       district,
        'priority':       priority,
        'disposition':    dispo,
        'council_district': council,
        'is_sapd':        True,
    }


def fetch_sapd_calls() -> list[dict]:
    """
    Fetch SAPD calls matching configured filters.
    Returns a list of normalized call dicts ready for dedup + alerting.
    """
    cfg = load_sapd_config()
    endpoint = cfg['api']['endpoint']
    alert_on = cfg.get('alert_on', [])

    params = _build_query(cfg)

    print(f"[sapd] Querying: {endpoint}")
    print(f"[sapd] Filter: {params.get('$where', '')}")

    try:
        resp = requests.get(
            endpoint,
            params=params,
            headers={'Accept': 'application/json', 'X-App-Token': ''},
            timeout=20,
        )
        resp.raise_for_status()
        records = resp.json()
    except Exception as e:
        print(f"[sapd] API error: {e}")
        return []

    print(f"[sapd] {len(records)} records returned from API")

    calls = []
    for record in records:
        call_type = record.get(cfg['fields']['call_type'], '')
        if _matches_alert_types(call_type, alert_on):
            calls.append(_normalize(record, cfg))

    print(f"[sapd] {len(calls)} calls matched alert filters")
    return calls


def build_sapd_discord_payload(calls: list[dict]) -> list[dict]:
    """Build Discord embeds for SAPD calls — grouped by call type."""
    from collections import Counter

    if not calls:
        return []

    type_counts = Counter(c['call_type'] for c in calls)
    summary = ' | '.join(f"{t}: {n}" for t, n in type_counts.most_common(5))

    embeds = []
    for call in calls[:10]:  # Discord limit
        priority = call.get('priority', '?')
        color = {
            '1': 0xef4444,  # red — highest priority
            '2': 0xf97316,  # orange
            '3': 0xeab308,  # yellow
            '4': 0x6b7280,  # gray — lowest
        }.get(str(priority), 0xf59e0b)

        embeds.append({
            "title": call['title'][:256],
            "description": call['description'][:400],
            "color": color,
            "footer": {"text": f"Priority {priority} · {call.get('published date', '')}"},
        })

    return [{
        "username": "NewsWatch — SAPD",
        "content": f"🚨 **SAPD Calls for Service** — {len(calls)} new alert(s)\n`{summary}`",
        "embeds": embeds,
    }]
