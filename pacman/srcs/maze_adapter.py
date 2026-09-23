"""Adapter between the game and an external 'A-Maze-ing' maze package.

Per the activity rules, this project must not implement its own maze
generator. Instead, it must adapt to whichever package is assigned by
another group. Since that package's exact call signature isn't known in
advance, this adapter tries a handful of common calling conventions and
normalizes whatever comes back into the game's own GameMaze shape. If
generation fails for any reason, a clean GenerationError is raised so
the caller can handle it without a traceback reaching the player.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:
    import maze_ing_stub as maze_package  # placeholder for the assigned package
except ImportError:  # pragma: no cover - defensive fallback
    maze_package = None  # type: ignore[assignment]


class GenerationError(Exception):
    """Raised when the external maze package cannot produce a maze."""


@dataclass
class GameMaze:
    """Normalized maze representation consumed by the rest of the game."""

    width: int
    height: int
    walls: List[List[bool]]


def _normalize(raw: object, width: int, height: int) -> GameMaze:
    """Convert an arbitrary package result into a GameMaze.

    Args:
        raw: Whatever object the external package returned.
        width: Expected maze width.
        height: Expected maze height.

    Returns:
        A validated GameMaze.

    Raises:
        GenerationError: If the result cannot be interpreted or is the
            wrong shape.
    """
    grid = getattr(raw, "grid", None)
    if grid is None and isinstance(raw, dict):
        grid = raw.get("grid")
    if grid is None:
        raise GenerationError("Maze package result has no usable 'grid' attribute.")

    walls = [[bool(cell) for cell in row] for row in grid]
    if len(walls) != height or any(len(row) != width for row in walls):
        raise GenerationError("Maze package returned a grid of unexpected size.")
    return GameMaze(width=width, height=height, walls=walls)


def generate_maze(width: int, height: int, seed: Optional[int] = None) -> GameMaze:
    """Generate a Pac-Man-compatible maze via the assigned external package.

    Args:
        width: Desired maze width (odd, >= 11).
        height: Desired maze height (odd, >= 11).
        seed: Optional seed for a reproducible layout (used for level 1).

    Returns:
        A GameMaze ready to be consumed by the game.

    Raises:
        GenerationError: If the package is missing or every known calling
            convention fails.
    """
    if maze_package is None:
        raise GenerationError("The 'A-Maze-ing' package is not installed.")

    attempts = (
        lambda: maze_package.generate(width=width, height=height, seed=seed, perfect=False),
        lambda: maze_package.generate(width, height, seed, False),
        lambda: maze_package.Maze(width, height, seed=seed, perfect=False),  # type: ignore[call-arg]
    )
    for attempt in attempts:
        try:
            raw = attempt()
        except Exception:
            continue
        try:
            return _normalize(raw, width, height)
        except GenerationError:
            continue

    raise GenerationError("Could not generate a maze with the assigned package.")