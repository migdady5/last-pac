"""Validate the external package and preserve its cell-edge wall encoding."""
from __future__ import annotations

import importlib
from collections import deque
from dataclasses import dataclass

DIRECTIONS = {(0, -1): (1, 4), (1, 0): (2, 8),
              (0, 1): (4, 1), (-1, 0): (8, 2)}


class GenerationError(Exception):
    """The external generator returned an unsupported or invalid maze."""


@dataclass
class GameMaze:
    """Shared collision and rendering representation."""
    width: int
    height: int
    edges: list[list[int]]
    blocked_cells: set[tuple[int, int]]

    @property
    def walls(self) -> list[list[bool]]:
        """Return solid-cell occupancy, separate from the thin wall edges."""
        return [[(x, y) in self.blocked_cells for x in range(self.width)]
                for y in range(self.height)]

    def can_move(self, x: int, y: int, dx: int, dy: int) -> bool:
        """Check both sides of a shared edge and exclude blocked cells."""
        if (dx, dy) not in DIRECTIONS:
            return False
        nx, ny = x + dx, y + dy
        if not (0 <= x < self.width and 0 <= y < self.height
                and 0 <= nx < self.width and 0 <= ny < self.height):
            return False
        if (x, y) in self.blocked_cells or (nx, ny) in self.blocked_cells:
            return False
        bit, opposite = DIRECTIONS[(dx, dy)]
        return not (self.edges[y][x] & bit or self.edges[ny][nx] & opposite)


def _normalize(raw: object, width: int, height: int) -> GameMaze:
    """Reject ambiguous grids instead of interpreting wall bits as booleans."""
    def get(name: str, default: object = None) -> object:
        return raw.get(name, default) if isinstance(raw, dict) else getattr(raw, name, default)

    if get('encoding') != 'edge_bits':
        raise GenerationError('Expected edge_bits encoding; adapt the assigned package interface explicitly.')
    grid = get('grid')
    if not isinstance(grid, (list, tuple)) or len(grid) != height:
        raise GenerationError('Unexpected grid height.')
    edges = []
    for row in grid:
        if not isinstance(row, (list, tuple)) or len(row) != width:
            raise GenerationError('Unexpected grid width.')
        if any(type(v) is not int or not 0 <= v <= 15 for v in row):
            raise GenerationError('Wall flags must be integers from 0 to 15.')
        edges.append(list(row))
    try:
        blocked = {tuple(cell) for cell in get('blocked_cells', ())}
        if any(len(cell) != 2 or any(type(v) is not int for v in cell)
               or not (0 <= cell[0] < width and 0 <= cell[1] < height)
               for cell in blocked):
            raise ValueError('Invalid blocked coordinate.')
    except (TypeError, ValueError) as exc:
        raise GenerationError('Invalid blocked_cells metadata.') from exc
    maze = GameMaze(width, height, edges, blocked)
    for y in range(height):
        for x in range(width):
            bits = edges[y][x]
            for (dx, dy), (bit, opposite) in DIRECTIONS.items():
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    if not bits & bit:
                        raise GenerationError('Open outer border.')
                elif bool(bits & bit) != bool(edges[ny][nx] & opposite):
                    raise GenerationError('Shared wall flags disagree.')
            if (x, y) in blocked and bits != 15:
                raise GenerationError('Blocked cells must have four closed walls.')
    available = {(x, y) for y in range(height) for x in range(width)} - blocked
    if not available:
        raise GenerationError('No playable cells.')
    seen = {next(iter(available))}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for dx, dy in DIRECTIONS:
            n = (x + dx, y + dy)
            if n not in seen and maze.can_move(x, y, dx, dy):
                seen.add(n)
                queue.append(n)
    if seen != available:
        raise GenerationError('Unreachable playable cells.')
    return maze


def generate_maze(width: int, height: int, seed: int | None = None,
                  package_name: str = 'maze_ing') -> GameMaze:
    """Call the configured external package with non-perfect generation."""
    try:
        package = importlib.import_module(package_name)
        raw = package.generate(width=width, height=height, seed=seed, perfect=False)
        return _normalize(raw, width, height)
    except GenerationError:
        raise
    except Exception as exc:
        raise GenerationError(f'Cannot use maze package {package_name}: {exc}') from exc
