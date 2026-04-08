"""
ingest.py — pull every RSS feed + Google News query in sources.yaml,
dedupe, and write raw/items.json for the scorer.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml
from bs4 import BeautifulSoup


def clean_text(s: str) -> str:
    if not s:
        return ""
    return BeautifulSoup(s, "html.parser").get_text(" ", strip=True)

ROOT = Path(__file__).parent
SOURCES_PATH = ROOT / "sources.yaml"
RAW_DIR = ROOT / "raw"
RAW_DIR.mkdir(exist_ok=True)

# Only items from the last N hours are considered fresh enough to ingest.
FRESH_HOURS = 36


def url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def google_news_rss(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en&gl=VN&ceid=VN:en"


def parse_published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        if getattr(entry, key, None):
            return datetime.fromtimestamp(time.mktime(getattr(entry, key)), tz=timezone.utc)
    return None


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def fetch_feed(name: str, url: str, meta: dict) -> list[dict]:
    items = []
    try:
        # Two-stage: requests pulls the bytes with a real browser UA,
        # then feedparser parses them. Many publishers (DSA, Reuters, WSJ,
        # KrAsia, Tech in Asia) 403 on default feedparser UA.
        import requests
        resp = requests.get(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  ! {name}: HTTP {resp.status_code}", file=sys.stderr)
            return items
        parsed = feedparser.parse(resp.content)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {name}: {exc}", file=sys.stderr)
        return items

    cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESH_HOURS)
    for entry in parsed.entries:
        link = getattr(entry, "link", "") or ""
        title = clean_text(getattr(entry, "title", "") or "")
        if not link or not title:
            continue
        published = parse_published(entry)
        if published and published < cutoff:
            continue
        summary = clean_text(getattr(entry, "summary", "") or "")
        items.append(
            {
                "id": url_hash(link),
                "title": title,
                "link": link,
                "summary": summary[:1200],
                "published": published.isoformat() if published else None,
                "source": name,
                "weight": meta.get("weight", 0.5),
                "section_hint": meta.get("section_hint"),
                "region": meta.get("region"),
                "language": meta.get("language", "en"),
                "sector": meta.get("sector"),
            }
        )
    return items


def main() -> None:
    sources = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    feeds = sources.get("rss_feeds", []) or []
    queries = sources.get("google_news_queries", []) or []

    all_items: list[dict] = []
    print(f"[ingest] {len(feeds)} RSS feeds + {len(queries)} Google News queries")

    for feed in feeds:
        name = feed["name"]
        url = feed["url"]
        items = fetch_feed(name, url, feed)
        print(f"  - {name}: {len(items)} fresh items")
        all_items.extend(items)

    for q in queries:
        name = f"Google News: {q['query']}"
        url = google_news_rss(q["query"])
        items = fetch_feed(name, url, q)
        print(f"  - {name}: {len(items)} fresh items")
        all_items.extend(items)

    # Dedupe by id (url hash) — keep highest-weight version
    by_id: dict[str, dict] = {}
    for item in all_items:
        existing = by_id.get(item["id"])
        if existing is None or item["weight"] > existing["weight"]:
            by_id[item["id"]] = item

    deduped = list(by_id.values())
    print(f"[ingest] {len(all_items)} total → {len(deduped)} after dedupe")

    out_path = RAW_DIR / "items.json"
    out_path.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ingest] wrote {out_path}")


if __name__ == "__main__":
    main()
