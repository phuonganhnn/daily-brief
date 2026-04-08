"""
render.py — read raw/synthesized.json and write docs/index.html.
The HTML is what gets deployed to GitHub Pages.
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

ROOT = Path(__file__).parent
SYNTHESIZED = ROOT / "raw" / "synthesized.json"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)
OUT = DOCS / "index.html"

SECTION_LABELS = {
    "ma": ("M&A Desk", "Deals, exits, structure & rationale"),
    "sector": ("Sector Pulse", "Giants, challengers, unit economics"),
    "regulatory": ("Regulatory & Macro", "Vietnam-first policy with implications"),
    "investor": ("Investor Watch", "Moves by tracked funds"),
    "reports": ("Reports", "Free PE/IB sector reports"),
}
SECTION_ORDER = ["ma", "sector", "regulatory", "investor", "reports"]


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Koru Brief — {{ generated_human }}</title>
<style>
  :root {
    --bg: #0b0b0f;
    --panel: #14141c;
    --border: #232333;
    --text: #e8e8f0;
    --muted: #8a8aa0;
    --accent: #ffb84d;
    --accent2: #6cd1ff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
    background: var(--bg); color: var(--text);
    line-height: 1.55; font-size: 16px;
  }
  header {
    padding: 28px 24px 16px; border-bottom: 1px solid var(--border);
    max-width: 980px; margin: 0 auto;
  }
  h1 { margin: 0 0 6px; font-size: 28px; font-weight: 700; }
  h1 .cat { color: var(--accent); }
  .timestamp { color: var(--muted); font-size: 14px; }
  main {
    max-width: 980px; margin: 0 auto; padding: 24px;
  }
  .section { margin-bottom: 40px; }
  .section h2 {
    font-size: 20px; margin: 0 0 4px;
    color: var(--accent);
    border-bottom: 2px solid var(--border); padding-bottom: 8px;
  }
  .section .sub { color: var(--muted); font-size: 13px; margin-bottom: 16px; }
  .item {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px; margin-bottom: 14px;
  }
  .item .meta {
    color: var(--muted); font-size: 12px; margin-bottom: 6px;
    display: flex; gap: 10px; flex-wrap: wrap;
  }
  .item .meta .src { color: var(--accent2); }
  .item h3 {
    margin: 0 0 8px; font-size: 16px; font-weight: 600;
  }
  .item h3 a { color: var(--text); text-decoration: none; }
  .item h3 a:hover { color: var(--accent); }
  .item .blurb { margin: 0 0 10px; }
  .item .question {
    background: rgba(255,184,77,0.08);
    border-left: 3px solid var(--accent);
    padding: 10px 12px; margin: 10px 0 0;
    font-size: 14px; color: #f0e6d4;
  }
  .item .question .label {
    color: var(--accent); font-weight: 600; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 4px;
  }
  .reflection {
    background: linear-gradient(180deg, rgba(108,209,255,0.08), rgba(108,209,255,0.02));
    border: 1px solid rgba(108,209,255,0.3);
    border-radius: 12px; padding: 20px; margin-top: 24px;
  }
  .reflection h2 { color: var(--accent2); margin: 0 0 10px; font-size: 18px; }
  .reflection p { margin: 0; font-size: 16px; }
  footer {
    text-align: center; color: var(--muted); font-size: 12px;
    padding: 24px; border-top: 1px solid var(--border); margin-top: 40px;
  }
  @media (max-width: 600px) {
    main { padding: 16px; }
    h1 { font-size: 22px; }
    .item { padding: 14px; }
  }
</style>
</head>
<body>
<header>
  <h1><span class="cat">●</span> Koru Brief</h1>
  <div class="timestamp">{{ generated_human }} · {{ items|length }} items</div>
</header>
<main>
{% for section_key in section_order %}
  {% set bucket = grouped[section_key] %}
  {% if bucket %}
  <div class="section">
    <h2>{{ labels[section_key][0] }}</h2>
    <div class="sub">{{ labels[section_key][1] }}</div>
    {% for it in bucket %}
    <div class="item">
      <div class="meta">
        <span class="src">{{ it.source }}</span>
        {% if it.region %}<span>· {{ it.region }}</span>{% endif %}
        {% if it.published %}<span>· {{ it.published[:10] }}</span>{% endif %}
        <span>· score {{ it.adjusted_score }}</span>
      </div>
      <h3><a href="{{ it.link }}" target="_blank" rel="noopener">{{ it.title }}</a></h3>
      <p class="blurb">{{ it.blurb }}</p>
      {% if it.question %}
      <div class="question">
        <span class="label">Think deeper · {{ it.framework_used or 'reflection' }}</span>
        {{ it.question }}
      </div>
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}
{% endfor %}

{% if reflection %}
<div class="reflection">
  <h2>Daily Reflection</h2>
  <p>{{ reflection }}</p>
</div>
{% endif %}
</main>
<footer>Generated 4× daily on Vietnam time · koru-brief · built for Phuong Anh</footer>
</body>
</html>
"""


def main() -> None:
    data = json.loads(SYNTHESIZED.read_text(encoding="utf-8"))
    items = data.get("items", [])
    grouped: dict[str, list[dict]] = {k: [] for k in SECTION_ORDER}
    for it in items:
        sec = it.get("section", "sector")
        if sec not in grouped:
            sec = "sector"
        grouped[sec].append(it)

    html = Template(TEMPLATE).render(
        generated_human=data.get("generated_human", ""),
        items=items,
        grouped=grouped,
        section_order=SECTION_ORDER,
        labels=SECTION_LABELS,
        reflection=data.get("reflection", ""),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"[render] wrote {OUT}")


if __name__ == "__main__":
    main()
