"""Loading and drawing game image assets."""

from __future__ import annotations

from pathlib import Path

import pygame

from src.constants import CELL_SIZE


class GameAssets:
    """Load and provide all graphical assets used by the game."""

    def __init__(self) -> None:
        """Load Pac-Man, ghosts, walls, and background images."""

        self.base_path = Path("assets/images")

        # ----------------------------------------------------------
        # Background
        # ----------------------------------------------------------
        self.background: pygame.Surface | None = None

        background_path = (
            self.base_path
            / "backgrounds"
            / "game_background.png"
        )

        if background_path.exists():
            self.background = pygame.image.load(
                str(background_path)
            ).convert()

        # ----------------------------------------------------------
        # Pac-Man images
        # ----------------------------------------------------------
        self.pacman_open = self._load_character(
            "open.png"
        )

        self.pacman_closed = self._load_character(
            "close.png"
        )

        # ----------------------------------------------------------
        # Ghost images
        # ----------------------------------------------------------
        self.ghosts: dict[str, dict[str, pygame.Surface]] = {}

        colors = (
            "blue",
            "green",
            "orange",
            "purple",
        )

        directions = (
            "up",
            "down",
            "left",
            "right",
        )

        for color in colors:

            self.ghosts[color] = {}

            for direction in directions:

                filename = (
                    f"{color}_{direction}.png"
                )

                self.ghosts[color][direction] = (
                    self._load_character(filename)
                )

        self.scared_ghost = self._load_character(
            "scared.png"
        )

        # ----------------------------------------------------------
        # Wall images
        # ----------------------------------------------------------
        self.wall_images = {
            "top": self._load_wall("top.png"),
            "bottom": self._load_wall("bottom.png"),
            "left": self._load_wall("left.png"),
            "right": self._load_wall("right.png"),
        }

    # ==============================================================
    # Image loading
    # ==============================================================

    def _load_character(
        self,
        filename: str,
    ) -> pygame.Surface:
        """Load a character small enough to fit inside a corridor."""

        path = self.base_path / "characters" / filename
        image = pygame.image.load(str(path)).convert_alpha()

        sprite_size = max(1, CELL_SIZE - 4)

        return pygame.transform.smoothscale(
            image,
            (sprite_size, sprite_size),
        )

    def _load_wall(
        self,
        filename: str,
    ) -> pygame.Surface:
        """Load and resize a wall image."""

        path = (
            self.base_path
            / "walls"
            / filename
        )

        image = pygame.image.load(
            str(path)
        ).convert_alpha()

        return pygame.transform.smoothscale(
            image,
            (CELL_SIZE, CELL_SIZE),
        )

    # ==============================================================
    # Background
    # ==============================================================

    def draw_background(
        self,
        screen: pygame.Surface,
    ) -> None:
        """Draw the arcade background across the entire window."""

        if self.background is None:

            screen.fill((0, 0, 0))
            return

        scaled_background = pygame.transform.smoothscale(
            self.background,
            screen.get_size(),
        )

        screen.blit(
            scaled_background,
            (0, 0),
        )

    # ==============================================================
    # Pac-Man
    # ==============================================================

    def pacman_image(
        self,
        direction: tuple[int, int],
        mouth_open: bool,
    ) -> pygame.Surface:
        """Return Pac-Man facing the requested direction."""

        image = (
            self.pacman_open
            if mouth_open
            else self.pacman_closed
        )

        if not mouth_open:
            return image

        # Original image faces right.
        if direction == (-1, 0):
            return pygame.transform.flip(
                image,
                True,
                False,
            )

        if direction == (0, -1):
            return pygame.transform.rotate(
                image,
                90,
            )

        if direction == (0, 1):
            return pygame.transform.rotate(
                image,
                -90,
            )

        return image

    # ==============================================================
    # Ghosts
    # ==============================================================

    def ghost_image(
        self,
        color: str,
        direction: tuple[int, int],
        scared: bool,
    ) -> pygame.Surface:
        """Return the correct ghost image."""

        if scared:
            return self.scared_ghost

        direction_name = "right"

        if direction == (-1, 0):
            direction_name = "left"

        elif direction == (1, 0):
            direction_name = "right"

        elif direction == (0, -1):
            direction_name = "up"

        elif direction == (0, 1):
            direction_name = "down"

        return self.ghosts[color][direction_name]

    # ==============================================================
    # Walls
    # ==============================================================

    def draw_wall(
        self,
        screen: pygame.Surface,
        walls: list[list[bool]],
        x: int,
        y: int,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Draw wall images only on edges facing a corridor or border."""

        if not walls[y][x]:
            return

        pixel_x = offset_x + x * CELL_SIZE
        pixel_y = offset_y + y * CELL_SIZE

        position = (pixel_x, pixel_y)

        height = len(walls)
        width = len(walls[y])

        # Keep the background from showing through solid walls.
        pygame.draw.rect(
            screen,
            (0, 0, 0),
            (
                pixel_x,
                pixel_y,
                CELL_SIZE,
                CELL_SIZE,
            ),
        )

        # Top edge.
        if y == 0 or not walls[y - 1][x]:
            screen.blit(
                self.wall_images["top"],
                position,
            )

        # Bottom edge.
        if y == height - 1 or not walls[y + 1][x]:
            screen.blit(
                self.wall_images["bottom"],
                position,
            )

        # Left edge.
        if x == 0 or not walls[y][x - 1]:
            screen.blit(
                self.wall_images["left"],
                position,
            )

        # Right edge.
        if x == width - 1 or not walls[y][x + 1]:
            screen.blit(
                self.wall_images["right"],
                position,
            )
