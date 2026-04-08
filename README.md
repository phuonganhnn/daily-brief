# koru-brief / daily-brief

A personal market briefing for a Vietnamese M&A analyst.
Pulls news from RSS + Google News, scores it against a reader profile,
synthesizes blurbs with Socratic questions, and publishes a static
HTML page 4× daily on Vietnam time (06:00 / 12:00 / 18:00 / 23:00 ICT).

Built lean. Runs on GitHub Actions free tier + Anthropic Haiku 4.5.
Target cost: <$5/month.

## Architecture

```
sources.yaml          → list of RSS feeds + Google News queries
reader_profile.yaml   → the "secret sauce" — sectors, geos, frameworks, watchlist
ingest.py             → pulls all feeds, dedupes, writes raw/items.json
score.py              → LLM relevance pass, keeps top ~25, assigns sections
synthesize.py         → blurb + Socratic question per item, batched reflection
render.py             → builds docs/index.html from a Jinja template
main.py               → orchestrator
.github/workflows/    → cron + GitHub Pages deploy
```

## Sections

1. **M&A Desk** — deals ≥USD 10mn, mechanics + thesis questions inline
2. **Sector Pulse** — giants and challengers in tracked sectors
3. **Reg & Macro (VN-first)** — only editorial-style regulatory items
4. **Investor Watch** — Quadria, Novo, TPG, Carlyle, Warburg, etc.
5. **Daily Reflection** — one synthesis question tying stories together

Plus a **Reports** sidebar surfacing free PE/IB sector reports.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # then edit .env to add your Anthropic key
python main.py
open docs/index.html
```

## Deploy

Pushed to `main` → GitHub Action runs on cron → static page deploys
to GitHub Pages at https://phuonganhnn.github.io/daily-brief/
