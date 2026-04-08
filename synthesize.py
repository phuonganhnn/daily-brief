"""
synthesize.py — for each scored item, generate a sharp-analyst blurb
plus an inline Socratic question. Then write a daily reflection that
ties two stories together.

Caches by item id so we never re-pay to synthesize the same URL twice.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "raw"
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "synth.json"
PROFILE_PATH = ROOT / "reader_profile.yaml"
SCORED = RAW_DIR / "scored.json"
SYNTHESIZED = RAW_DIR / "synthesized.json"

MODEL = "claude-haiku-4-5-20251001"

load_dotenv(ROOT / ".env", override=True)
client = Anthropic()


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def synth_prompt() -> str:
    profile = PROFILE_PATH.read_text(encoding="utf-8")
    return f"""You write blurbs for a daily market briefing.
The reader is a senior investment analyst at a Vietnamese boutique merchant bank.
Profile (YAML):

```yaml
{profile}
```

For the news item I send you, return a JSON object with:
- blurb: 3-5 sentences in a SHARP ANALYST voice. Facts first, then 'so what'.
  No hedging. Never use the banned_phrases. If the item is in Vietnamese,
  translate to English in the blurb.
- question: ONE inline Socratic question following the question_style rules
  for this item's section. Keep it concrete and answerable in 5 minutes of
  thinking.

  IMPORTANT: bias HEAVILY toward second-order thinking. Roughly half of all
  questions should be second-order ("If X is true, what does this force
  competitor Y to do? What does the market look like 12-24 months out? Who
  is the non-obvious loser? What does this make INEVITABLE next?"). Avoid
  generic 'what does this mean' questions — every question should name a
  specific party, force, or time horizon.

- framework_used: which framework from frameworks_preference inspired the
  question (string, e.g. "second-order thinking", "reverse engineering")

Return ONLY a JSON object. No prose, no markdown fences.
"""


def synthesize_item(item: dict, system_prompt: str) -> dict:
    payload = {
        "title": item["title"],
        "summary": item["summary"][:800],
        "source": item["source"],
        "section": item.get("section"),
        "language": item.get("language", "en"),
    }
    resp = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"blurb": item["title"], "question": "", "framework_used": ""}


def write_reflection(items: list[dict], system_prompt: str) -> str:
    top = [
        {"title": it["title"], "blurb": it.get("blurb", ""), "section": it.get("section")}
        for it in items[:10]
    ]
    user = (
        "Read these top stories from today's brief and write ONE synthesis question "
        "that ties at least two of them together. The question should force the reader "
        "to apply reverse-engineering or second-order thinking. Return only the question, "
        "one or two sentences, no preamble.\n\n"
        + json.dumps(top, ensure_ascii=False)
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def main() -> None:
    items = json.loads(SCORED.read_text(encoding="utf-8"))
    print(f"[synth] {len(items)} scored items")
    cache = load_cache()
    system_prompt = synth_prompt()

    enriched = []
    for it in items:
        cached = cache.get(it["id"])
        if cached:
            enriched.append({**it, **cached})
            continue
        result = synthesize_item(it, system_prompt)
        cache[it["id"]] = result
        enriched.append({**it, **result})
        print(f"  + {it['title'][:60]}")

    reflection = write_reflection(enriched, system_prompt) if enriched else ""
    now_ict = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    output = {
        "generated_at_ict": now_ict.isoformat(),
        "generated_human": now_ict.strftime("%A, %d %B %Y — %H:%M ICT"),
        "items": enriched,
        "reflection": reflection,
    }
    SYNTHESIZED.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    save_cache(cache)
    print(f"[synth] wrote {SYNTHESIZED}")


if __name__ == "__main__":
    main()
