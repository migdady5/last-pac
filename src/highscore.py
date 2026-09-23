"""Persistent, JSON-backed highscore system."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict


class HighscoreEntry(TypedDict):
    """A single highscore record."""

    name: str
    score: int


_NAME_RE = re.compile(r"^[A-Za-z0-9 ]{1,10}$")


class HighscoreManager:
    """Loads, validates and persists the top-10 highscore list."""

    def __init__(self, filename: str) -> None:
        """Load existing scores from disk (or start empty on any error).

        Args:
            filename: Path to the JSON file used for storage.
        """
        self.filename = filename
        self.scores: list[HighscoreEntry] = self._load()

    def _load(self) -> list[HighscoreEntry]:
        """Load and validate saved scores, returning an empty list on error."""
        path = Path(self.filename)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"[highscore] Warning: could not read '{self.filename}'. Starting empty.")
            return []
        if not isinstance(data, list):
            return []

        cleaned: list[HighscoreEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))[:10]
            try:
                score = int(item.get("score", 0))
            except (TypeError, ValueError):
                continue
            if score < 0 or not _NAME_RE.match(name):
                continue
            cleaned.append({"name": name, "score": score})
        cleaned.sort(key=lambda entry: entry["score"], reverse=True)
        return cleaned[:10]

    def save(self) -> None:
        """Persist the current top-10 scores to disk."""
        try:
            Path(self.filename).write_text(json.dumps(self.scores, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"[highscore] Warning: could not save scores ({exc}).")

    def add_score(self, name: str, score: int) -> bool:
        """Validate and insert a new score, keeping only the top 10.

        Args:
            name: Player name; sanitized to max 10 alphanumeric/space chars.
            score: The player's final score (clamped to non-negative).

        Returns:
            True if the score made it into the persisted top 10.
        """
        clean_name = re.sub(r"[^A-Za-z0-9 ]", "", (name or "Player").strip())
        clean_name = clean_name[:10] or "Player"
        try:
            clean_score = max(0, int(score))
        except (TypeError, ValueError):
            clean_score = 0

        self.scores.append({"name": clean_name, "score": clean_score})
        self.scores.sort(key=lambda entry: entry["score"], reverse=True)
        made_it = {"name": clean_name, "score": clean_score} in self.scores[:10]
        self.scores = self.scores[:10]
        self.save()
        return made_it

    def top(self, count: int = 10) -> list[HighscoreEntry]:
        """Return the top ``count`` highscores, best first."""
        return self.scores[:count]