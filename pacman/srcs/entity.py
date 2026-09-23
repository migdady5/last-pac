"""Player and Ghost entity classes."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

Direction = Tuple[int, int]
UP: Direction = (0, -1)
DOWN: Direction = (0, 1)
LEFT: Direction = (-1, 0)
RIGHT: Direction = (1, 0)
STOP: Direction = (0, 0)
ALL_DIRECTIONS: Tuple[Direction, ...] = (UP, DOWN, LEFT, RIGHT)


class GhostState(Enum):
    """Behavioral state of a ghost."""

    CHASE = "chase"
    EDIBLE = "edible"
    EATEN = "eaten"


def _is_walkable(walls: List[List[bool]], x: int, y: int) -> bool:
    """Return True if (x, y) is inside the maze and not a wall."""
    if y < 0 or y >= len(walls) or x < 0 or x >= len(walls[0]):
        return False
    return not walls[y][x]


def _distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Manhattan distance between two grid cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class Player:
    """The Pac-Man character, moving on a grid one cell at a time."""

    x: int
    y: int
    direction: Direction = STOP
    next_direction: Direction = STOP

    def set_direction(self, direction: Direction) -> None:
        """Queue the desired next movement direction."""
        self.next_direction = direction

    def step(self, walls: List[List[bool]]) -> None:
        """Advance the player by exactly one grid cell, if possible.

        Args:
            walls: The maze wall grid.
        """
        nx, ny = self.x + self.next_direction[0], self.y + self.next_direction[1]
        if self.next_direction != STOP and _is_walkable(walls, nx, ny):
            self.direction = self.next_direction

        mx, my = self.x + self.direction[0], self.y + self.direction[1]
        if _is_walkable(walls, mx, my):
            self.x, self.y = mx, my
        else:
            self.direction = STOP


@dataclass
class Ghost:
    """An enemy ghost with simple chase/flee/eaten behavior."""

    x: int
    y: int
    home_x: int
    home_y: int
    color: Tuple[int, int, int]
    state: GhostState = GhostState.CHASE
    direction: Direction = STOP
    edible_timer: float = 0.0
    eaten_timer: float = 0.0
    frozen: bool = False

    def update_timers(self, dt: float) -> None:
        """Progress the ghost's edible/eaten countdown timers.

        Args:
            dt: Elapsed seconds since the last update.
        """
        if self.state == GhostState.EDIBLE:
            self.edible_timer -= dt
            if self.edible_timer <= 0:
                self.state = GhostState.CHASE
        elif self.state == GhostState.EATEN:
            self.eaten_timer -= dt
            if self.eaten_timer <= 0 and (self.x, self.y) == (self.home_x, self.home_y):
                self.state = GhostState.CHASE

    def step(self, walls: List[List[bool]], player_pos: Tuple[int, int],
              rng: random.Random) -> None:
        """Advance the ghost by exactly one grid cell.

        Args:
            walls: The maze wall grid.
            player_pos: Current (x, y) of the player, used as chase target.
            rng: Random source for unpredictability and tie-breaking.
        """
        if self.frozen:
            return

        target = (self.home_x, self.home_y) if self.state == GhostState.EATEN else player_pos

        options = [d for d in ALL_DIRECTIONS
                   if _is_walkable(walls, self.x + d[0], self.y + d[1])]
        if not options:
            return

        reverse = (-self.direction[0], -self.direction[1])
        non_reverse = [d for d in options if d != reverse]
        if non_reverse:
            options = non_reverse

        if self.state == GhostState.EDIBLE:
            options.sort(key=lambda d: -_distance((self.x + d[0], self.y + d[1]), target))
        else:
            options.sort(key=lambda d: _distance((self.x + d[0], self.y + d[1]), target))

        if self.state == GhostState.CHASE and rng.random() < 0.15:
            rng.shuffle(options)

        chosen = options[0]
        self.direction = chosen
        self.x += chosen[0]
        self.y += chosen[1]

    def make_edible(self, duration: float) -> None:
        """Switch the ghost to its edible, fleeing state."""
        if self.state != GhostState.EATEN:
            self.state = GhostState.EDIBLE
            self.edible_timer = duration

    def get_eaten(self, respawn_delay: float) -> None:
        """Switch the ghost to its eaten state and send it home."""
        self.state = GhostState.EATEN
        self.eaten_timer = respawn_delay