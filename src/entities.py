"""Player and Ghost entity classes."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from src.maze_adapter import GameMaze

Direction = tuple[int, int]
UP: Direction = (0, -1)
DOWN: Direction = (0, 1)
LEFT: Direction = (-1, 0)
RIGHT: Direction = (1, 0)
STOP: Direction = (0, 0)
ALL_DIRECTIONS: tuple[Direction, ...] = (UP, DOWN, LEFT, RIGHT)


class GhostState(Enum):
    """Behavioral state of a ghost."""

    CHASE = "chase"
    EDIBLE = "edible"
    EATEN = "eaten"


def _distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Manhattan distance between two grid cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class Player:
    """Move smoothly between walkable grid-cell centers."""

    x: int
    y: int
    direction: Direction = STOP
    next_direction: Direction = STOP
    _progress: float = field(default=0.0, init=False)
    _moving: bool = field(default=False, init=False)

    @property
    def render_x(self) -> float:
        """Return the interpolated horizontal drawing position."""
        return self.x + self.direction[0] * self._progress

    @property
    def render_y(self) -> float:
        """Return the interpolated vertical drawing position."""
        return self.y + self.direction[1] * self._progress

    def set_direction(self, direction: Direction) -> None:
        """Queue a turn to take at the next available cell center."""
        self.next_direction = direction

    def advance(
        self,
        walls: GameMaze,
        dt: float,
        interval: float,
    ) -> tuple[float, bool]:
        """Move toward the next cell using elapsed seconds.

        Return unused time and whether a new cell center was reached.
        The interval is the time required to cross one complete cell.
        Grid coordinates change only on arrival, for pellet checks.
        """
        if dt <= 0:
            return 0.0, False
        if interval <= 0:
            raise ValueError("Movement interval must be positive.")

        if not self._moving:
            dx, dy = self.next_direction
            if self.next_direction != STOP and walls.can_move(self.x, self.y, dx, dy):
                self.direction = self.next_direction

            dx, dy = self.direction
            if self.direction == STOP or not walls.can_move(self.x, self.y, dx, dy):
                self.direction = STOP
                return 0.0, False
            self._moving = True

        needed = (1.0 - self._progress) * interval
        if dt < needed:
            self._progress += dt / interval
            return 0.0, False

        self.x += self.direction[0]
        self.y += self.direction[1]
        self._progress = 0.0
        self._moving = False
        return max(0.0, dt - needed), True

    def step(self, walls: GameMaze) -> None:
        """Reach the next cell center for legacy grid-step callers.

        The game's smooth update loop uses advance() instead.
        """
        self.advance(walls, 1.0, 1.0)


@dataclass
class Ghost:
    """An enemy moving smoothly between grid-cell centers."""

    x: int
    y: int
    home_x: int
    home_y: int
    color: tuple[int, int, int]
    state: GhostState = GhostState.CHASE
    direction: Direction = STOP
    edible_timer: float = 0.0
    eaten_timer: float = 0.0
    frozen: bool = False
    _progress: float = field(default=0.0, init=False)
    _moving: bool = field(default=False, init=False)

    @property
    def render_x(self) -> float:
        """Return the interpolated horizontal drawing position."""
        return self.x + self.direction[0] * self._progress

    @property
    def render_y(self) -> float:
        """Return the interpolated vertical drawing position."""
        return self.y + self.direction[1] * self._progress

    def reset_home(self) -> None:
        """Reset position, animation progress, and state after a life loss."""
        self.x, self.y = self.home_x, self.home_y
        self.direction = STOP
        self._progress = 0.0
        self._moving = False
        self.state = GhostState.CHASE
        self.edible_timer = 0.0
        self.eaten_timer = 0.0

    def update_timers(self, dt: float) -> None:
        """Update scared time and revive eaten ghosts once home."""
        dt = max(0.0, dt)
        if self.state == GhostState.EDIBLE:
            self.edible_timer = max(0.0, self.edible_timer - dt)
            if self.edible_timer <= 0:
                self.state = GhostState.CHASE
        elif self.state == GhostState.EATEN:
            self.eaten_timer = max(0.0, self.eaten_timer - dt)
            if (
                self.eaten_timer <= 0
                and not self._moving
                and (self.x, self.y) == (self.home_x, self.home_y)
            ):
                self.state = GhostState.CHASE

    def _home_direction(self, walls: GameMaze) -> Direction:
        """Find the first step of a shortest walkable route home."""
        queue: deque[tuple[int, int, Direction]] = deque(
            [(self.x, self.y, STOP)]
        )
        visited = {(self.x, self.y)}
        while queue:
            x, y, first = queue.popleft()
            if (x, y) == (self.home_x, self.home_y):
                return first
            for direction in ALL_DIRECTIONS:
                nx, ny = x + direction[0], y + direction[1]
                if (nx, ny) not in visited and walls.can_move(x, y, direction[0], direction[1]):
                    visited.add((nx, ny))
                    queue.append((
                        nx, ny, direction if first == STOP else first
                    ))
        return STOP

    def _choose_direction(
        self,
        walls: GameMaze,
        player_pos: tuple[int, int],
        rng: random.Random,
    ) -> Direction:
        """Choose chase/flee movement at a cell center only."""
        if self.state == GhostState.EATEN:
            return self._home_direction(walls)

        options = [
            d for d in ALL_DIRECTIONS
            if walls.can_move(self.x, self.y, d[0], d[1])
        ]
        if not options:
            return STOP
        reverse = (-self.direction[0], -self.direction[1])
        non_reverse = [d for d in options if d != reverse]
        if non_reverse:
            options = non_reverse
        options.sort(
            key=lambda d: _distance(
                (self.x + d[0], self.y + d[1]), player_pos
            ),
            reverse=self.state == GhostState.EDIBLE,
        )
        if self.state == GhostState.CHASE and rng.random() < 0.15:
            rng.shuffle(options)
        return options[0]

    def advance(
        self,
        walls: GameMaze,
        player_pos: tuple[int, int],
        rng: random.Random,
        dt: float,
        interval: float,
    ) -> tuple[float, bool]:
        """Move toward a cell; return unused seconds and arrival status."""
        if dt <= 0 or self.frozen:
            return 0.0, False
        if interval <= 0:
            raise ValueError("Movement interval must be positive.")

        if not self._moving:
            self.direction = self._choose_direction(walls, player_pos, rng)
            if self.direction == STOP:
                return 0.0, False
            self._moving = True

        needed = (1.0 - self._progress) * interval
        if dt < needed:
            self._progress += dt / interval
            return 0.0, False

        self.x += self.direction[0]
        self.y += self.direction[1]
        self._progress = 0.0
        self._moving = False
        return max(0.0, dt - needed), True

    def step(
        self,
        walls: GameMaze,
        player_pos: tuple[int, int],
        rng: random.Random,
    ) -> None:
        """Reach the next cell center for legacy grid-step callers."""
        self.advance(walls, player_pos, rng, 1.0, 1.0)

    def make_edible(self, duration: float) -> None:
        """Start scared behavior without snapping the drawing position."""
        if self.state != GhostState.EATEN:
            self.state = GhostState.EDIBLE
            self.edible_timer = duration

    def get_eaten(self, respawn_delay: float) -> None:
        """Finish the current segment, then travel home to respawn."""
        self.state = GhostState.EATEN
        self.eaten_timer = respawn_delay
