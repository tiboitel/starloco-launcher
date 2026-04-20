"""Configuration load/save via JSON."""

import json
from pathlib import Path

CONFIG_PATH = Path("config/config.json")


def load() -> dict:
    """Load config from JSON file.

    Returns:
        Dict of config values, empty if file doesn't exist.
    """
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict) -> None:
    """Save config to JSON file.

    Args:
        data: Dict of config values to serialize.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def get(key: str, default=None):
    """Get a config value.

    Args:
        key: Config key to retrieve.
        default: Default if key missing.

    Returns:
        Config value or default.
    """
    return load().get(key, default)


def put(key: str, value) -> None:
    """Set a config value.

    Args:
        key: Config key to set.
        value: Value to store.
    """
    data = load()
    data[key] = value
    save(data)
