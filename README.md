# NewsWatch 📰

A configurable keyword news monitor that runs on **GitHub Actions** (free) and delivers alerts to Discord, email, RSS, and a GitHub Pages dashboard.

Follows the same pattern as the Texas Surveillance Contract Watcher — same SQLite dedup, same GitHub Pages output, same Actions cron setup.

---

## Features

- **Multiple configurable topics** — each with its own keyword list and output settings
- **Discord webhook alerts** — rich embeds grouped by topic
- **Email alerts** — clean dark-themed HTML via Gmail SMTP
- **RSS feed** — served via GitHub Pages, subscribe in any reader
- **Live dashboard** — GitHub Pages site with ticker, topic sidebar, and article cards
- **Deduplication** — SQLite tracks seen articles so you never get the same alert twice
- **Runs free** — GitHub Actions cron, no server needed

---

## Setup

### 1. Fork / clone this repo

```
git clone https://github.com/YOUR_USERNAME/news-keyword-monitor
cd news-keyword-monitor
```

### 2. Configure your topics

Edit `config/topics.yml`. Each topic block looks like:

```yaml
- name: "My Topic"
  keywords:
    - "keyword one"
    - "another phrase"
  max_results: 10
  outputs:
    discord: true
    email: false
    rss: true
```

Add as many topics as you want.

### 3. Add GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Required | Description |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | If using Discord | From channel Settings → Integrations → Webhooks |
| `SMTP_USER` | If using email | Your Gmail address |
| `SMTP_PASS` | If using email | Gmail [App Password](https://myaccount.google.com/apppasswords) (not your real password) |
| `EMAIL_TO` | If using email | Destination address |

### 4. Enable GitHub Pages

Go to **Settings → Pages**:
- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/docs`

Your dashboard will be at: `https://YOUR_USERNAME.github.io/news-keyword-monitor`

### 5. Enable GitHub Actions

The workflow file is already at `.github/workflows/monitor.yml`. It will run automatically every 6 hours.

To **run it immediately**: go to **Actions → NewsWatch Monitor → Run workflow**.

---

## Running locally

```bash
pip install -r requirements.txt

# Optional: set env vars for alerts
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export SMTP_USER="you@gmail.com"
export SMTP_PASS="your-app-password"
export EMAIL_TO="you@gmail.com"

python src/main.py
```

Dashboard and RSS will be written to `docs/`.

---

## File structure

```
news-keyword-monitor/
├── .github/workflows/monitor.yml   # GitHub Actions cron
├── config/topics.yml               # YOUR KEYWORD CONFIG — edit this
├── src/
│   ├── main.py                     # Orchestrator
│   ├── scraper.py                  # gnews + RSS fallback
│   ├── dedup.py                    # SQLite deduplication
│   ├── alerts.py                   # Discord + email
│   ├── rss_gen.py                  # RSS XML generator
│   └── dashboard_gen.py            # HTML dashboard generator
├── data/seen.db                    # SQLite (git-ignored, Actions-cached)
├── docs/                           # Generated output → GitHub Pages
│   ├── index.html                  # Dashboard
│   └── feed.xml                    # RSS feed
└── requirements.txt
```

---

## Customizing the schedule

Edit the cron line in `.github/workflows/monitor.yml`:

```yaml
- cron: '0 */6 * * *'   # every 6 hours (default)
- cron: '0 8 * * *'     # once daily at 8am UTC
- cron: '*/30 * * * *'  # every 30 minutes
```

---

## Notes

- **News source**: Uses [gnews](https://github.com/ranahaani/GNews) (no API key needed) with a Google News RSS fallback. For higher volume, consider adding a free [NewsAPI](https://newsapi.org) key.
- **DB persistence**: The SQLite file is cached between Actions runs via `actions/cache`. It rotates monthly to avoid unbounded growth.
- **Rate limiting**: There's a 1.2s delay between keyword requests to be polite to Google News.
