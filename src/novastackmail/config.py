import json
import os
import re
from pathlib import Path
from typing import Optional


def config_path() -> Path:
    override = os.environ.get("NOVASTACKMAIL_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "novastackmail" / "config.json"


def normalize_config(data):
    if not isinstance(data, dict):
        return None
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
        # Migrate the original single-session format without requiring login again.
        if data.get("access_token"):
            profiles["default"] = {
                "access_token": data.get("access_token"),
                "expires_at": data.get("expires_at"),
                "mailbox": data.get("mailbox") or {},
                "api_base": data.get("api_base"),
            }
        data["profiles"] = profiles
    data["active_profile"] = data.get("active_profile") if data.get("active_profile") in profiles else (next(iter(profiles), None))
    return data


def load_config(path: Optional[Path] = None):
    target = Path(path) if path else config_path()
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return normalize_config(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def active_profile(data):
    if not isinstance(data, dict):
        return {}
    profiles = data.get("profiles") or {}
    name = data.get("active_profile")
    profile = profiles.get(name) if name else None
    if isinstance(profile, dict):
        return profile
    return {}


def validate_profile_name(name):
    return isinstance(name, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", name))


def save_config(data, path: Optional[Path] = None) -> Path:
    target = Path(path) if path else config_path()
    normalized = normalize_config(data) or {"profiles": {}, "active_profile": None}
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)
        handle.write("\\n")
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
