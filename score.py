"""
score.py — load raw items + reader profile, ask Claude Haiku to score
each item 0-100 for relevance and assign it to a section, return top 25.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "raw"
PROFILE_PATH = ROOT / "reader_profile.yaml"
RAW_ITEMS = RAW_DIR / "items.json"
SCORED_ITEMS = RAW_DIR / "scored.json"

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 30
TOP_N = 25
SECTIONS = ["ma", "sector", "regulatory", "investor", "reports"]

load_dotenv(ROOT / ".env", override=True)
client = Anthropic()


def build_profile_prompt() -> str:
    profile = PROFILE_PATH.read_text(encoding="utf-8")
    return f"""You are the relevance gatekeeper for a daily market briefing.
The reader is a senior investment analyst at a Vietnamese boutique merchant bank.
Here is their full profile (YAML):

```yaml
{profile}
```

Your job: read a batch of news items and for EACH item return a JSON object with:
- id: the item id (copy verbatim)
- score: integer 0-100 for relevance to this reader
- section: one of {SECTIONS}
  - "ma" = M&A deals, acquisitions, buyouts, exits (≥USD 10mn or VN target)
  - "sector" = business news on sector giants/challengers, unit economics
  - "regulatory" = VN policy / FDI / sector incentives — ONLY editorial-style
  - "investor" = moves by watchlist funds/people
  - "reports" = free PE/IB sector reports (Bain, McKinsey, EY, BCG, etc.)
- reason: <15 word justification

Scoring guide:
- 90+ : must include, perfect fit
- 70-89: strong include
- 50-69: borderline, only if section is light
- <50: drop

Apply the always_drop filters strictly. If an item is pure stock-tick,
vanity award, generic political headline, or crypto/Web3, score it <30.

Return ONLY a JSON array, no prose, no markdown fences.
"""


def score_batch(items: list[dict], system_prompt: str) -> list[dict]:
    payload = [
        {"id": it["id"], "title": it["title"], "summary": it["summary"][:400], "source": it["source"]}
        for it in items
    ]
    user_msg = "Score these items:\n\n" + json.dumps(payload, ensure_ascii=False)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        print(f"  ! batch parse failed: {exc}\n{text[:300]}")
        return []


def main() -> None:
    items = json.loads(RAW_ITEMS.read_text(encoding="utf-8"))
    print(f"[score] {len(items)} raw items")
    if not items:
        SCORED_ITEMS.write_text("[]", encoding="utf-8")
        return

    system_prompt = build_profile_prompt()
    scored_by_id: dict[str, dict] = {}

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        print(f"  scoring batch {i // BATCH_SIZE + 1} ({len(batch)} items)")
        results = score_batch(batch, system_prompt)
        for r in results:
            scored_by_id[r["id"]] = r

    enriched = []
    for it in items:
        s = scored_by_id.get(it["id"])
        if not s:
            continue
        # Apply source weight as a small multiplier
        adjusted = s["score"] * (0.7 + 0.3 * it.get("weight", 0.5))
        enriched.append({**it, **s, "adjusted_score": round(adjusted, 1)})

    enriched.sort(key=lambda x: x["adjusted_score"], reverse=True)
    top = enriched[:TOP_N]
    print(f"[score] kept top {len(top)} of {len(enriched)} scored")
    SCORED_ITEMS.write_text(json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
