from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hapa_graphify.narrative import main


if __name__ == "__main__":
    raise SystemExit(main(["--generate-images", *sys.argv[1:]]))
