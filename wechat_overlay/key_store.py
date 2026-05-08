from __future__ import annotations

from pathlib import Path


DEFAULT_KEY_PATH = Path.home() / ".wechat_overlay_key"


def load_key(path: Path = DEFAULT_KEY_PATH) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def save_key(key: str, path: Path = DEFAULT_KEY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key, encoding="utf-8")
