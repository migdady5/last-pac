from __future__ import annotations

import random
from dataclasses import dataclass

PATTERN_42 = ('1000111', '1000001', '1110111', '0010100', '0010111')
DIRECTIONS = ((0, -1, 1, 4), (1, 0, 2, 8), (0, 1, 4, 1), (-1, 0, 8, 2))


@dataclass
class Maze:
    """Each grid cell holds N=1, E=2, S=4, W=8 wall bits."""

    width: int
    height: int
    grid: list[list[int]]
    blocked_cells: set[tuple[int, int]]
    encoding: str = 'edge_bits'


def generate(
    width: int,
    height: int,
    seed: int | None = None,
    perfect: bool = True,
) -> Maze:
    """Carve connected passages around reserved 42 cells."""
    if width < 11 or height < 11:
        raise ValueError('Maze must be at least 11 by 11.')

    rng = random.Random(seed)
    sx, sy = (width - 7) // 2, (height - 5) // 2
    blocked = {
        (sx + x, sy + y)
        for y, row in enumerate(PATTERN_42)
        for x, value in enumerate(row)
        if value == '1'
    }

    grid = [[15] * width for _ in range(height)]
    visited = {(width // 2, height // 2)}
    stack = list(visited)

    while stack:
        x, y = stack[-1]
        options = [
            (dx, dy, bit, opposite)
            for dx, dy, bit, opposite in DIRECTIONS
            if 0 <= x + dx < width
            and 0 <= y + dy < height
            and (x + dx, y + dy) not in blocked
            and (x + dx, y + dy) not in visited
        ]

        if not options:
            stack.pop()
            continue

        dx, dy, bit, opposite = rng.choice(options)
        nx, ny = x + dx, y + dy
        grid[y][x] &= ~bit
        grid[ny][nx] &= ~opposite
        visited.add((nx, ny))
        stack.append((nx, ny))

    if len(visited) != width * height - len(blocked):
        raise ValueError('Reserved cells disconnect the maze.')

    if not perfect:
        # Remove shared edges only between valid cells; never touch the 42.
        candidates = []

        for y in range(height):
            for x in range(width):
                if (x, y) in blocked:
                    continue

                for dx, dy, bit, opposite in (
                    DIRECTIONS[1],
                    DIRECTIONS[2],
                ):
                    nx, ny = x + dx, y + dy
                    if (
                        nx < width
                        and ny < height
                        and (nx, ny) not in blocked
                        and grid[y][x] & bit
                    ):
                        candidates.append(
                            (x, y, nx, ny, bit, opposite)
                        )

        rng.shuffle(candidates)
        count = max(1, width * height // 5)
        for x, y, nx, ny, bit, opposite in candidates[:count]:
            grid[y][x] &= ~bit
            grid[ny][nx] &= ~opposite

    return Maze(width, height, grid, blocked)
