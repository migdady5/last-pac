"""Level construction on top of a generated maze."""

from __future__ import annotations

import random

from src.constants import GHOST_COLORS
from src.entities import Ghost
from src.maze_adapter import GameMaze


def _nearest_open_cell(
        walls: list[list[bool]], target: tuple[int, int]) -> tuple[int, int]:
    """Breadth-first search for the closest non-wall cell to ``target``."""
    height, width = len(walls), len(walls[0])
    tx, ty = target
    tx = min(max(tx, 0), width - 1)
    ty = min(max(ty, 0), height - 1)
    if not walls[ty][tx]:
        return tx, ty

    visited: set[tuple[int, int]] = {(tx, ty)}
    queue: list[tuple[int, int]] = [(tx, ty)]
    while queue:
        cx, cy = queue.pop(0)
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height and (
                    nx, ny) not in visited:
                if not walls[ny][nx]:
                    return nx, ny
                visited.add((nx, ny))
                queue.append((nx, ny))
    return tx, ty  # pragma: no cover - unreachable for valid mazes


class Level:
    """Holds the maze, collectibles, ghosts and player start for one level."""

    def __init__(
            self,
            maze: GameMaze,
            pacgum_target: int,
            rng: random.Random) -> None:
        """Build a playable level from a raw maze.

        Args:
            maze: The normalized maze from the maze adapter.
            pacgum_target: Desired number of regular pacgums (config value).
            rng: Random source used to pick pacgum placement.
        """
        self.maze = maze
        self.width = maze.width
        self.height = maze.height
        self.walls = maze.walls
        self.pattern_42_cells = set(maze.blocked_cells)

        self.player_start = _nearest_open_cell(
            self.walls, (self.width // 2, self.height // 2))

        corners = [
            (0, 0),
            (self.width - 1, 0),
            (0, self.height - 1),
            (self.width - 1, self.height - 1),
        ]
        self.super_pacgums: set[tuple[int, int]] = {
            _nearest_open_cell(self.walls, corner) for corner in corners
        }

        open_cells = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if not self.walls[y][x]
            and (x, y) != self.player_start
            and (x, y) not in self.super_pacgums
        ]
        rng.shuffle(open_cells)
        count = min(pacgum_target, len(open_cells)
                    ) if pacgum_target > 0 else len(open_cells)
        self.pacgums: set[tuple[int, int]] = set(open_cells[:count])

        ghost_names = list(GHOST_COLORS.items())
        self.ghosts: list[Ghost] = []
        for (gx, gy), (name, color) in zip(corners, ghost_names):
            hx, hy = _nearest_open_cell(self.walls, (gx, gy))
            self.ghosts.append(
                Ghost(x=hx, y=hy, home_x=hx, home_y=hy, color=color))
            _ = name  # kept for clarity / potential future per-ghost behavior

    def total_collectibles(self) -> int:
        """Total number of pacgums + super-pacgums in this level."""
        return len(self.pacgums) + len(self.super_pacgums)

    def remaining_collectibles(self) -> int:
        """Number of pacgums + super-pacgums not yet eaten."""
        return len(self.pacgums) + len(self.super_pacgums)
