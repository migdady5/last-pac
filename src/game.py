"""Main game state machine: menu, gameplay, pause, and end screens."""

from __future__ import annotations

import random
from enum import Enum, auto
from typing import Any

import pygame

from src import ui
from src.assets import GameAssets
from src.constants import (
    CELL_SIZE,
    COLOR_PACGUM,
    COLOR_SUPER_PACGUM,
    EDIBLE_DURATION,
    FPS,
    GHOST_MOVE_INTERVAL,
    GHOST_RESPAWN_DELAY,
    PLAYER_MOVE_INTERVAL,
)
from src.entities import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    GhostState,
    Player,
)
from src.highscore import HighscoreManager
from src.level import Level
from src.maze_adapter import (
    GenerationError,
    generate_maze,
)


# ==============================================================
# Layout
# ==============================================================

SIDE_MARGIN = 100
TOP_MARGIN = 110
BOTTOM_MARGIN = 80


class State(Enum):
    """Top-level game states."""

    MENU = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    PLAYING = auto()
    PAUSED = auto()
    ENTER_NAME = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    QUIT = auto()


_KEY_DIRECTIONS = {
    pygame.K_UP: UP,
    pygame.K_w: UP,

    pygame.K_DOWN: DOWN,
    pygame.K_s: DOWN,

    pygame.K_LEFT: LEFT,
    pygame.K_a: LEFT,

    pygame.K_RIGHT: RIGHT,
    pygame.K_d: RIGHT,
}


class Game:
    """Own pygame and control the game."""

    def __init__(
        self,
        config: dict[str, Any],
    ) -> None:
        """Initialize the game."""

        self.config = config

        self.highscores = HighscoreManager(
            config["highscore_filename"]
        )

        pygame.init()

        pygame.display.set_caption(
            "Pac-Man"
        )

        self.max_width = max(
            level["width"]
            for level in config["levels"]
        )

        self.max_height = max(
            level["height"]
            for level in config["levels"]
        )

        window_width = (
            self.max_width * CELL_SIZE
            + SIDE_MARGIN * 2
        )

        window_height = (
            self.max_height * CELL_SIZE
            + TOP_MARGIN
            + BOTTOM_MARGIN
        )

        self.screen = pygame.display.set_mode(
            (
                window_width,
                window_height,
            )
        )

        self.clock = pygame.time.Clock()

        self.assets = GameAssets()

        self.title_font = pygame.font.SysFont(
            "couriernew",
            42,
            bold=True,
        )

        self.font = pygame.font.SysFont(
            "couriernew",
            22,
        )

        self.small_font = pygame.font.SysFont(
            "couriernew",
            16,
        )

        self.hud_font = pygame.font.SysFont(
            "couriernew",
            24,
            bold=True,
        )

        self.state = State.MENU

        self.menu_selected = 0
        self.pause_selected = 0

        self.name_input = ""

        self.rng = random.Random()

        self.level_index = 0

        self.level: Level | None = None

        self.player: Player | None = None

        self.score = 0

        self.lives = config["lives"]

        self.time_left = float(
            config["level_max_time"]
        )

        self.victory = False

        self.cheat_mode = False

        self.invincible = False

        self.ghosts_frozen = False

        self.speed_multiplier = 1.0

    # ==============================================================
    # Maze screen position
    # ==============================================================

    def _maze_origin(
        self,
    ) -> tuple[int, int]:
        """Return the top-left pixel of the current maze."""

        assert self.level is not None

        maze_width = (
            len(self.level.walls[0])
            * CELL_SIZE
        )

        maze_height = (
            len(self.level.walls)
            * CELL_SIZE
        )

        maximum_width = (
            self.max_width
            * CELL_SIZE
        )

        maximum_height = (
            self.max_height
            * CELL_SIZE
        )

        x = (
            SIDE_MARGIN
            + (
                maximum_width
                - maze_width
            ) // 2
        )

        y = (
            TOP_MARGIN
            + (
                maximum_height
                - maze_height
            ) // 2
        )

        return x, y

    # ==============================================================
    # Level / game lifecycle
    # ==============================================================

    def _build_level(
        self,
        level_index: int,
    ) -> bool:
        """Generate and prepare one level."""

        spec = self.config["levels"][
            level_index
        ]

        seed = (
            self.config["seed"]
            if level_index == 0
            else None
        )

        try:

            maze = generate_maze(
                spec["width"],
                spec["height"],
                seed=seed,
                package_name=(
                    self.config[
                        "maze_package"
                    ]
                ),
            )

        except GenerationError as exc:

            print(
                "[maze] Error generating "
                f"level {level_index + 1}: "
                f"{exc}"
            )

            return False

        level_rng = (
            random.Random(seed)
            if seed is not None
            else self.rng
        )

        try:
            self.level = Level(
                maze,
                self.config["pacgum"],
                level_rng,
            )
        except ValueError as exc:
            print(f"[maze] Cannot prepare level: {exc}")
            return False

        self.player = Player(
            *self.level.player_start
        )

        self.time_left = float(
            self.config["level_max_time"]
        )

        return True

    def start_new_game(
        self,
    ) -> None:
        """Start a new game."""

        self.score = 0

        self.lives = self.config[
            "lives"
        ]

        self.level_index = 0
        self.cheat_mode = False
        self._reset_cheat_effects()

        if self._build_level(
            self.level_index
        ):
            self.state = State.PLAYING

        else:
            self.state = State.MENU

    def _restart_current_level(
        self,
        lose_life: bool,
    ) -> None:
        """Restart the current level."""

        if lose_life:
            self.lives -= 1

        if self.lives <= 0:

            self._end_game(
                victory=False
            )

            return

        if not self._build_level(
            self.level_index
        ):
            self._end_game(
                victory=False
            )

    def _respawn_after_hit(
        self,
    ) -> None:
        """Respawn after a ghost collision."""

        assert self.level is not None

        self.lives -= 1

        if self.lives <= 0:

            self._end_game(
                victory=False
            )

            return

        self.player = Player(
            *self.level.player_start
        )

        for ghost in self.level.ghosts:
            ghost.reset_home()

    def _advance_level(
        self,
    ) -> None:
        """Advance to the next level."""

        self.level_index += 1

        if self.level_index >= len(
            self.config["levels"]
        ):

            self._end_game(
                victory=True
            )

            return

        if not self._build_level(
            self.level_index
        ):

            self._end_game(
                victory=False
            )

    def _end_game(
        self,
        victory: bool,
    ) -> None:
        """Finish the game."""

        self.victory = victory

        self.name_input = ""

        self.state = State.ENTER_NAME

    # ==============================================================
    # Update
    # ==============================================================

    def _update_playing(self, dt: float) -> None:
        """Move all characters together and check collisions along the way."""
        assert self.level is not None
        assert self.player is not None

        moving_player = self.player
        current_level = self.level
        previous_lives = self.lives
        walls = current_level.maze
        move_interval = (
            PLAYER_MOVE_INTERVAL / max(self.speed_multiplier, 0.1)
        )

        # Small shared steps keep fast characters from crossing unnoticed.
        max_step = min(1.0 / 120.0, move_interval / 4.0,
                       GHOST_MOVE_INTERVAL / 4.0)
        remaining = max(0.0, dt)
        while remaining > 0:
            step_dt = min(remaining, max_step)
            remaining = max(0.0, remaining - step_dt)
            self.time_left -= step_dt
            if self.time_left <= 0:
                self._restart_current_level(lose_life=not self.invincible)
                return

            for ghost in current_level.ghosts:
                ghost.update_timers(step_dt)

            player_time = step_dt
            while player_time > 0:
                player_time, arrived = moving_player.advance(
                    walls, player_time, move_interval
                )
                if arrived:
                    self._handle_collectibles()

            if not self.ghosts_frozen:
                for ghost in current_level.ghosts:
                    ghost_time = step_dt
                    while ghost_time > 0:
                        ghost_time, _ = ghost.advance(
                            walls,
                            (moving_player.x, moving_player.y),
                            self.rng,
                            ghost_time,
                            GHOST_MOVE_INTERVAL,
                        )

            self._handle_ghost_collisions()
            if (
                self.player is not moving_player
                or self.level is not current_level
                or self.lives != previous_lives
                or self.state != State.PLAYING
            ):
                return

            if not current_level.pacgums and not current_level.super_pacgums:
                self._advance_level()
                return

    def _handle_collectibles(
        self,
    ) -> None:
        """Eat pacgums."""

        assert self.level is not None
        assert self.player is not None

        position = (
            self.player.x,
            self.player.y,
        )

        if position in self.level.pacgums:

            self.level.pacgums.discard(
                position
            )

            self.score += self.config[
                "points_per_pacgum"
            ]

        elif (
            position
            in self.level.super_pacgums
        ):

            self.level.super_pacgums.discard(
                position
            )

            self.score += self.config[
                "points_per_super_pacgum"
            ]

            for ghost in self.level.ghosts:

                ghost.make_edible(
                    EDIBLE_DURATION
                )

    def _handle_ghost_collisions(
        self,
    ) -> None:
        """Handle collisions with ghosts."""

        assert self.level is not None
        assert self.player is not None

        for ghost in self.level.ghosts:

            dx = ghost.render_x - self.player.render_x
            dy = ghost.render_y - self.player.render_y
            if dx * dx + dy * dy > 0.65 ** 2:
                continue

            # Nearby sprites separated by a closed edge cannot collide.
            px = int(self.player.render_x + 0.5)
            py = int(self.player.render_y + 0.5)
            gx = int(ghost.render_x + 0.5)
            gy = int(ghost.render_y + 0.5)
            if (px, py) != (gx, gy) and not self.level.maze.can_move(
                px, py, gx - px, gy - py
            ):
                continue

            if (
                ghost.state
                == GhostState.EDIBLE
            ):

                ghost.get_eaten(
                    GHOST_RESPAWN_DELAY
                )

                self.score += self.config[
                    "points_per_ghost"
                ]

            elif (
                ghost.state
                == GhostState.CHASE
                and not self.invincible
            ):

                self._respawn_after_hit()

                return

    # ==============================================================
    # Input
    # ==============================================================

    def _handle_event(
        self,
        event: pygame.event.Event,
    ) -> None:
        """Handle pygame events."""

        if event.type == pygame.QUIT:

            self.state = State.QUIT

            return

        if event.type != pygame.KEYDOWN:
            return

        if self.state == State.MENU:

            self._handle_menu_key(
                event.key
            )

        elif self.state in (
            State.INSTRUCTIONS,
            State.HIGHSCORES,
        ):

            if event.key in (
                pygame.K_RETURN,
                pygame.K_ESCAPE,
            ):
                self.state = State.MENU

        elif self.state == State.PLAYING:

            self._handle_playing_key(
                event.key
            )

        elif self.state == State.PAUSED:

            self._handle_pause_key(
                event.key
            )

        elif self.state == State.ENTER_NAME:

            self._handle_name_key(
                event
            )

    def _handle_menu_key(
        self,
        key: int,
    ) -> None:
        """Handle the main menu."""

        if key in (
            pygame.K_UP,
            pygame.K_w,
        ):

            self.menu_selected = (
                self.menu_selected - 1
            ) % 4

        elif key in (
            pygame.K_DOWN,
            pygame.K_s,
        ):

            self.menu_selected = (
                self.menu_selected + 1
            ) % 4

        elif key == pygame.K_RETURN:

            if self.menu_selected == 0:

                self.start_new_game()

            elif self.menu_selected == 1:

                self.state = (
                    State.HIGHSCORES
                )

            elif self.menu_selected == 2:

                self.state = (
                    State.INSTRUCTIONS
                )

            else:

                self.state = State.QUIT

    def _handle_playing_key(
        self,
        key: int,
    ) -> None:
        """Handle gameplay keys."""

        assert self.player is not None

        if key in _KEY_DIRECTIONS:

            self.player.set_direction(
                _KEY_DIRECTIONS[key]
            )

        elif key == pygame.K_p:

            self.pause_selected = 0

            self.state = State.PAUSED

        elif key == pygame.K_c:

            self.cheat_mode = not self.cheat_mode
            if not self.cheat_mode:
                self._reset_cheat_effects()

        elif self.cheat_mode:

            self._handle_cheat_key(
                key
            )

    def _reset_cheat_effects(self) -> None:
        """Restore normal movement and vulnerability; keep earned progress."""
        self.invincible = False
        self.ghosts_frozen = False
        self.speed_multiplier = 1.0
        if self.level is not None:
            for ghost in self.level.ghosts:
                ghost.frozen = False

    def _handle_cheat_key(self, key: int) -> None:
        """Apply reviewer controls only during active cheat-mode gameplay."""
        if not self.cheat_mode or self.state != State.PLAYING:
            return
        if key == pygame.K_i:
            self.invincible = not self.invincible
        elif key == pygame.K_f:
            self.ghosts_frozen = not self.ghosts_frozen
        elif key == pygame.K_l:
            self.lives += 1
        elif key == pygame.K_k:
            self._advance_level()
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed_multiplier = min(self.speed_multiplier + 0.5, 4.0)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_multiplier = max(self.speed_multiplier - 0.5, 0.5)
        elif key == pygame.K_r:
            self._reset_cheat_effects()

    def _draw_cheat_panel(self) -> None:
        """Show controls and active effects below the maze."""
        width, height = self.screen.get_size()
        panel = pygame.Rect(8, height - 72, width - 16, 66)
        pygame.draw.rect(self.screen, (7, 12, 25), panel, border_radius=8)
        pygame.draw.rect(self.screen, (80, 125, 180), panel, 1,
                         border_radius=8)
        if self.cheat_mode:
            lines = [
                'CHEAT MODE ON | C: disable | R: reset effects',
                f'I: invincible {"ON" if self.invincible else "OFF"}   '
                f'F: freeze {"ON" if self.ghosts_frozen else "OFF"}   '
                f'Speed: {self.speed_multiplier:.1f}x',
                'K: skip level   L: +1 life   +/-: player speed',
            ]
        else:
            lines = ['C: enable reviewer cheat mode']
        for index, text in enumerate(lines):
            label = self.small_font.render(text, True, (220, 235, 255))
            if label.get_width() > panel.width - 16:
                ratio = (panel.width - 16) / label.get_width()
                label = pygame.transform.smoothscale(
                    label, (panel.width - 16,
                            max(1, round(label.get_height() * ratio))))
            self.screen.blit(label, (panel.x + 10, panel.y + 6 + index * 18))

    def _handle_pause_key(
        self,
        key: int,
    ) -> None:
        """Handle pause menu."""

        if key in (
            pygame.K_UP,
            pygame.K_w,
            pygame.K_DOWN,
            pygame.K_s,
        ):

            self.pause_selected = (
                1 - self.pause_selected
            )

        elif key == pygame.K_RETURN:

            if self.pause_selected == 0:

                self.state = State.PLAYING

            else:

                self.state = State.MENU

        elif key == pygame.K_p:

            self.state = State.PLAYING

    def _handle_name_key(
        self,
        event: pygame.event.Event,
    ) -> None:
        """Handle highscore name input."""

        if event.key == pygame.K_RETURN:

            self.highscores.add_score(
                self.name_input or "Player",
                self.score,
            )

            self.state = (
                State.VICTORY
                if self.victory
                else State.GAME_OVER
            )

        elif event.key == pygame.K_BACKSPACE:

            self.name_input = (
                self.name_input[:-1]
            )

        elif (
            event.unicode.isalnum()
            or event.unicode == " "
        ):

            if len(self.name_input) < 10:

                self.name_input += (
                    event.unicode
                )

    # ==============================================================
    # HUD
    # ==============================================================

    def _draw_live_hud(
        self,
    ) -> None:
        """Draw the real score, lives, level and timer."""

        width = self.screen.get_width()

        # Cover fake HUD from the background.
        hud_surface = pygame.Surface(
            (
                width,
                TOP_MARGIN,
            ),
            pygame.SRCALPHA,
        )

        hud_surface.fill(
            (0, 0, 0, 205)
        )

        self.screen.blit(
            hud_surface,
            (0, 0),
        )

        title = self.title_font.render(
            "PAC-MAN",
            True,
            (255, 220, 0),
        )

        title_rect = title.get_rect(
            center=(
                width // 2,
                TOP_MARGIN // 2,
            )
        )

        self.screen.blit(
            title,
            title_rect,
        )

        score_text = self.hud_font.render(
            f"SCORE  {self.score}",
            True,
            (255, 255, 255),
        )

        lives_text = self.hud_font.render(
            f"LIVES  {self.lives}",
            True,
            (255, 255, 255),
        )

        level_text = self.hud_font.render(
            f"LEVEL  {self.level_index + 1}",
            True,
            (255, 255, 255),
        )

        time_text = self.hud_font.render(
            f"TIME  {int(max(self.time_left, 0))}",
            True,
            (255, 255, 255),
        )

        self.screen.blit(
            score_text,
            (25, 25),
        )

        self.screen.blit(
            lives_text,
            (25, 60),
        )

        self.screen.blit(
            level_text,
            (
                width
                - level_text.get_width()
                - 25,
                25,
            ),
        )

        self.screen.blit(
            time_text,
            (
                width
                - time_text.get_width()
                - 25,
                60,
            ),
        )

    # ==============================================================
    # Rendering
    # ==============================================================

    def _render_playing(
        self,
    ) -> None:
        """Draw gameplay."""

        assert self.level is not None
        assert self.player is not None

        # ----------------------------------------------------------
        # Background
        # ----------------------------------------------------------
        self.assets.draw_background(
            self.screen
        )

        maze_x, maze_y = (
            self._maze_origin()
        )

        maze_width = (
            len(self.level.walls[0])
            * CELL_SIZE
        )

        maze_height = (
            len(self.level.walls)
            * CELL_SIZE
        )

        # ----------------------------------------------------------
        # Cover the fake maze in the background.
        # This is where the REAL maze is placed.
        # ----------------------------------------------------------
        maze_panel = pygame.Surface(
            (
                maze_width,
                maze_height,
            ),
            pygame.SRCALPHA,
        )

        maze_panel.fill(
            (15, 15, 18, 255)
        )

        self.screen.blit(
            maze_panel,
            (
                maze_x,
                maze_y,
            ),
        )

        # Blue border around real maze.
        pygame.draw.rect(
            self.screen,
            (0, 90, 255),
            pygame.Rect(
                maze_x - 4,
                maze_y - 4,
                maze_width + 8,
                maze_height + 8,
            ),
            width=4,
            border_radius=8,
        )

        # ----------------------------------------------------------
        # Walls
        # ----------------------------------------------------------
        # Fill reserved cells; draw every shared edge exactly once.
        for x, y in self.level.pattern_42_cells:
            pygame.draw.rect(
                self.screen, (60, 80, 200),
                (maze_x + x * CELL_SIZE, maze_y + y * CELL_SIZE,
                 CELL_SIZE, CELL_SIZE),
            )
        for y, row in enumerate(self.level.maze.edges):
            for x, bits in enumerate(row):
                px, py = maze_x + x * CELL_SIZE, maze_y + y * CELL_SIZE
                color = (190, 190, 195)
                if bits & 1:
                    pygame.draw.line(self.screen, color, (px, py),
                                     (px + CELL_SIZE, py), 1)
                if bits & 8:
                    pygame.draw.line(self.screen, color, (px, py),
                                     (px, py + CELL_SIZE), 1)
                if x == self.level.width - 1 and bits & 2:
                    pygame.draw.line(self.screen, color, (px + CELL_SIZE, py),
                                     (px + CELL_SIZE, py + CELL_SIZE), 1)
                if y == self.level.height - 1 and bits & 4:
                    pygame.draw.line(self.screen, color, (px, py + CELL_SIZE),
                                     (px + CELL_SIZE, py + CELL_SIZE), 1)

        # ----------------------------------------------------------
        # Pacgums
        # ----------------------------------------------------------
        for x, y in self.level.pacgums:

            center = (
                maze_x
                + x * CELL_SIZE
                + CELL_SIZE // 2,
                maze_y
                + y * CELL_SIZE
                + CELL_SIZE // 2,
            )

            pygame.draw.circle(
                self.screen,
                COLOR_PACGUM,
                center,
                3,
            )

        # ----------------------------------------------------------
        # Super pacgums
        # ----------------------------------------------------------
        for (
            x,
            y,
        ) in self.level.super_pacgums:

            center = (
                maze_x
                + x * CELL_SIZE
                + CELL_SIZE // 2,
                maze_y
                + y * CELL_SIZE
                + CELL_SIZE // 2,
            )

            pygame.draw.circle(
                self.screen,
                COLOR_SUPER_PACGUM,
                center,
                7,
            )

        # ----------------------------------------------------------
        # Ghosts
        # ----------------------------------------------------------
        ghost_colors = (
            "blue",
            "green",
            "orange",
            "purple",
        )

        for index, ghost in enumerate(
            self.level.ghosts
        ):

            scared = (
                ghost.state
                == GhostState.EDIBLE
            )

            ghost_image = (
                self.assets.ghost_image(
                    ghost_colors[
                        index
                        % len(ghost_colors)
                    ],
                    ghost.direction,
                    scared,
                )
            )

            ghost_rect = ghost_image.get_rect(
                center=(
                    round(maze_x + (ghost.render_x + 0.5) * CELL_SIZE),
                    round(maze_y + (ghost.render_y + 0.5) * CELL_SIZE),
                )
            )
            self.screen.blit(ghost_image, ghost_rect)

        # ----------------------------------------------------------
        # Pac-Man animation
        # ----------------------------------------------------------
        mouth_open = (
            pygame.time.get_ticks()
            // 150
        ) % 2 == 0

        player_image = (
            self.assets.pacman_image(
                self.player.direction,
                mouth_open,
            )
        )

        player_rect = player_image.get_rect(
            center=(
                round(
                    maze_x + (self.player.render_x + 0.5) * CELL_SIZE
                ),
                round(
                    maze_y + (self.player.render_y + 0.5) * CELL_SIZE
                ),
            )
        )
        self.screen.blit(player_image, player_rect)

        # ----------------------------------------------------------
        # Real HUD
        # ----------------------------------------------------------
        self._draw_live_hud()

        self._draw_cheat_panel()

    def _render(
        self,
    ) -> None:
        """Render current game state."""

        if self.state == State.MENU:

            ui.draw_main_menu(
                self.screen,
                self.title_font,
                self.font,
                self.small_font,
                self.highscores.top(),
                self.menu_selected,
            )

        elif self.state == State.INSTRUCTIONS:

            ui.draw_instructions(
                self.screen,
                self.font,
                self.small_font,
            )

        elif self.state == State.HIGHSCORES:

            ui.draw_highscores(
                self.screen,
                self.font,
                self.small_font,
                self.highscores.top(),
            )

        elif self.state in (
            State.PLAYING,
            State.PAUSED,
        ):

            self._render_playing()

            if self.state == State.PAUSED:

                ui.draw_pause_menu(
                    self.screen,
                    self.font,
                    self.pause_selected,
                )

        elif self.state == State.ENTER_NAME:

            ui.draw_end_screen(
                self.screen,
                self.title_font,
                self.font,
                self.victory,
                self.score,
                self.name_input,
            )

        elif self.state in (
            State.GAME_OVER,
            State.VICTORY,
        ):

            ui.draw_end_screen(
                self.screen,
                self.title_font,
                self.font,
                self.state
                == State.VICTORY,
                self.score,
                self.name_input,
            )

        pygame.display.flip()

    # ==============================================================
    # Main loop
    # ==============================================================

    def run(
        self,
    ) -> None:
        """Run until the player quits."""

        try:

            while self.state != State.QUIT:

                dt = (
                    self.clock.tick(FPS)
                    / 1000.0
                )

                for event in pygame.event.get():

                    self._handle_event(
                        event
                    )

                    if (
                        event.type
                        == pygame.KEYDOWN
                        and self.state
                        in (
                            State.GAME_OVER,
                            State.VICTORY,
                        )
                        and event.key
                        == pygame.K_RETURN
                    ):

                        self.state = (
                            State.MENU
                        )

                if self.state == State.PLAYING:

                    self._update_playing(
                        dt
                    )

                self._render()

        except Exception as exc:

            print(
                "[game] Unexpected error, "
                "shutting down cleanly: "
                f"{exc}"
            )

        finally:

            pygame.quit()
