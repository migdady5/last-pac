"""Configuration loading and validation for the Pac-Man game.

The configuration file is JSON with optional comment lines (starting
with '#' or '//') and optional C-style block comments. Any error while
reading or parsing the file results in a warning message and a fallback
to safe defaults -- the game must never crash because of a bad config.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "highscore_filename": "highscores.json",
    "levels": [{"width": 21, "height": 21} for _ in range(10)],
    "lives": 3,
    "pacgum": 150,
    "points_per_pacgum": 10,
    "points_per_super_pacgum": 50,
    "points_per_ghost": 200,
    "seed": 42,
    "level_max_time": 90,
    "maze_package": "maze_ing_stub",
}


def _strip_comments(text: str) -> str:
    """Remove '#', '//' line comments and '/* */' block comments.

    Args:
        text: Raw file content.

    Returns:
        A comment-free string safe to pass to ``json.loads``.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        cleaned_lines.append(re.sub(r"(?<!:)//.*$", "", line))
    return "\n".join(cleaned_lines)


def _clamp_int(
    value: Any,
    default: int,
    key: str,
    minimum: int = 0,
) -> int:
    """Coerce a value to a bounded integer and report invalid values."""
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        print(f"[config] Warning: '{key}' is invalid. Using {default}.")
        return default
    if ivalue < minimum:
        print(
            f"[config] Warning: '{key}' must be at least {minimum}."
            f" Using {default}.")
        return default
    return ivalue


def _validate_levels(value: Any) -> list[dict[str, int]]:
    """Validate the 'levels' array, ensuring odd, minimum-sized mazes."""
    if not isinstance(value, list) or not value:
        print("[config] Warning: 'levels' must be a non-empty array."
              " Using defaults.")
        return [dict(item) for item in DEFAULT_CONFIG["levels"]]

    levels: list[dict[str, int]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        width = _clamp_int(item.get("width"), 21, "level width", minimum=11)
        height = _clamp_int(item.get("height"), 21, "level height", minimum=11)
        if width % 2 == 0:
            print(
                f"[config] Warning: level width {width} is even; using {
                    width + 1}.")
            width += 1
        if height % 2 == 0:
            print(
                f"[config] Warning: level height {height} is even; using {
                    height + 1}.")
            height += 1
        levels.append({"width": width, "height": height})
    if not levels:
        print("[config] Warning: no valid levels found. Using defaults.")
        return [dict(item) for item in DEFAULT_CONFIG["levels"]]
    return levels


def load_config(path: str) -> dict[str, Any]:
    """Load, parse and validate a JSON-with-comments configuration file.

    Args:
        path: Path to the configuration file (must have a .json suffix).

    Returns:
        A fully populated, validated configuration dictionary. Missing or
        invalid keys silently fall back to defaults; unknown keys are
        ignored.
    """
    config: dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
    file_path = Path(path)

    if not file_path.exists():
        print(
            f"[config] Warning: file '{path}' not found. "
            "Using default configuration.")
        return config

    if file_path.suffix.lower() != ".json":
        print(
            f"[config] Warning: '{path}' does not have a .json extension. "
            "Using defaults.")
        return config

    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"[config] Warning: could not read '{path}' ({exc}). "
            "Using defaults.")
        return config

    cleaned = _strip_comments(raw)
    try:
        data: Any = json.loads(cleaned) if cleaned.strip() else {}
    except json.JSONDecodeError as exc:
        print(
            f"[config] Warning: invalid JSON in '{path}' ({exc}). "
            "Using defaults.")
        return config

    if not isinstance(data, dict):
        print("[config] Warning: config root must be a JSON object. "
              "Using defaults.")
        return config

    for key in DEFAULT_CONFIG:
        if key not in data:
            print(f"[config] Warning: missing '{key}'. Using default value.")
            continue
        value = data[key]
        if key == "levels":
            config["levels"] = _validate_levels(value)
        elif key == "highscore_filename":
            if isinstance(value, str) and value.strip():
                config["highscore_filename"] = value
            else:
                print("[config] Warning: invalid highscore filename. "
                      "Using default.")
        elif key == "maze_package":
            if isinstance(value, str) and value.strip():
                config["maze_package"] = value.strip()
            else:
                print("[config] Warning: invalid maze package name. "
                      "Using default.")
        else:
            minimum = 1 if key in {"lives", "level_max_time"} else 0
            config[key] = _clamp_int(value, DEFAULT_CONFIG[key], key, minimum)

    return config
