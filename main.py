"""
main.py — orchestrate the four stages: ingest → score → synthesize → render.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
STAGES = ["ingest.py", "score.py", "synthesize.py", "render.py"]


def main() -> None:
    for stage in STAGES:
        print(f"\n========== {stage} ==========")
        result = subprocess.run([sys.executable, str(ROOT / stage)], cwd=ROOT)
        if result.returncode != 0:
            print(f"!! {stage} failed with code {result.returncode}", file=sys.stderr)
            sys.exit(result.returncode)
    print("\n[main] done. Open docs/index.html")


if __name__ == "__main__":
    main()
