from __future__ import annotations

import json
from pathlib import Path

from relevar.models import Inventario


def write_json(inv: Inventario, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(inv.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
