import json
import os
from pathlib import Path
from typing import Optional


def config_path() -> Path:
    override = os.environ.get("NOVASTACKMAIL_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "novastackmail" / "config.json"


def load_config(path: Optional[Path] = None):
    target = Path(path) if path else config_path()
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_config(data, path: Optional[Path] = None) -> Path:
    target = Path(path) if path else config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(target)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def clear_config(path: Optional[Path] = None) -> None:
    target = Path(path) if path else config_path()
    try:
        target.unlink()
    except FileNotFoundError:
        pass
