"""Shared constants for the Pac-Man activity."""
from __future__ import annotations

CELL_SIZE = 24
HUD_HEIGHT = 40

COLOR_BG = (0, 0, 0)
COLOR_WALL = (33, 33, 222)
COLOR_PACGUM = (255, 255, 200)
COLOR_SUPER_PACGUM = (255, 255, 255)
COLOR_PLAYER = (255, 255, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_HIGHLIGHT = (0, 220, 220)
COLOR_DANGER = (220, 40, 40)

GHOST_COLORS = {
    "blinky": (220, 40, 40),
    "pinky": (255, 150, 200),
    "inky": (80, 220, 220),
    "clyde": (255, 165, 0),
}
GHOST_EDIBLE_COLOR = (40, 40, 220)

FPS = 60
PLAYER_MOVE_INTERVAL = 0.14  # seconds per grid cell at normal speed
GHOST_MOVE_INTERVAL = 0.18
EDIBLE_DURATION = 7.0
GHOST_RESPAWN_DELAY = 6.0