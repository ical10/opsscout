from __future__ import annotations

import json
from pathlib import Path


def _path(key: str, cache_dir: Path) -> Path:
    return cache_dir / f"{key}.json"


def read(key: str, cache_dir: Path) -> dict | None:
    path = _path(key, cache_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(key: str, payload: dict, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _path(key, cache_dir).write_text(json.dumps(payload), encoding="utf-8")
