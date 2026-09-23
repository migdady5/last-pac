"""Main game state machine: menu, gameplay, pause, and end screens."""
from __future__ import annotations

import random
import sys
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import pygame

from src import ui
from src.constants import (
    CELL_SIZE,
    COLOR_BG,
    COLOR_PACGUM,
    COLOR_PLAYER,
    COLOR_SUPER_PACGUM,
    COLOR_WALL,
    EDIBLE_DURATION,
    FPS,
    GHOST_EDIBLE_COLOR,
    GHOST_MOVE_INTERVAL,
    GHOST_RESPAWN_DELAY,
    HUD_HEIGHT,
    PLAYER_MOVE_INTERVAL,
)
from src.entities import DOWN, LEFT, RIGHT, STOP, UP, GhostState, Player
from src.highscore import HighscoreManager
from src.level import Level
from src.maze_adapter import GenerationError, generate_maze


class State(Enum):
    """Top-level game states."""

    MENU = auto()
    INSTRUCTIONS = auto()
    PLAYING = auto()
    PAUSED = auto()
    ENTER_NAME = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    QUIT = auto()


_KEY_DIRECTIONS = {
    pygame.K_UP: UP, pygame.K_w: UP,
    pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
}


class Game:
    """Owns the pygame window and drives the full game loop."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize pygame, load highscores, and prepare the first level.

        Args:
            config: A validated configuration dictionary (see src.config).
        """
        self.config = config
        self.highscores = HighscoreManager(config["highscore_filename"])

        pygame.init()
        pygame.display.set_caption("Pac-Man")
        max_width = max(level["width"] for level in config["levels"])
        max_height = max(level["height"] for level in config["levels"])
        self.screen = pygame.display.set_mode(
            (max_width * CELL_SIZE, max_height * CELL_SIZE + HUD_HEIGHT)
        )
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("couriernew", 42, bold=True)
        self.font = pygame.font.SysFont("couriernew", 22)
        self.small_font = pygame.font.SysFont("couriernew", 16)

        self.state = State.MENU
        self.menu_selected = 0
        self.pause_selected = 0
        self.name_input = ""

        self.rng = random.Random()
        self.level_index = 0
        self.level: Optional[Level] = None
        self.player: Optional[Player] = None
        self.score = 0
        self.lives = config["lives"]
        self.time_left = float(config["level_max_time"])
        self.player_move_timer = 0.0
        self.ghost_move_timer = 0.0
        self.victory = False

        self.cheat_mode = False
        self.invincible = False
        self.ghosts_frozen = False
        self.speed_multiplier = 1.0

    # ------------------------------------------------------------------
    # Level / game lifecycle
    # ------------------------------------------------------------------
    def _build_level(self, level_index: int) -> bool:
        """Generate and populate a level, handling generator failures.

        Args:
            level_index: Zero-based index into config['levels'].

        Returns:
            True on success, False if generation failed (game continues
            gracefully with an error message rather than crashing).
        """
        spec = self.config["levels"][level_index]
        seed = self.config["seed"] if level_index == 0 else None
        try:
            maze = generate_maze(spec["width"], spec["height"], seed=seed)
        except GenerationError as exc:
            print(f"[maze] Error generating level {level_index + 1}: {exc}")
            return False

        level_rng = random.Random(seed) if seed is not None else self.rng
        self.level = Level(maze, self.config["pacgum"], level_rng)
        self.player = Player(*self.level.player_start)
        self.time_left = float(self.config["level_max_time"])
        self.ghosts_frozen = False
        return True

    def start_new_game(self) -> None:
        """Reset score/lives and start level 1."""
        self.score = 0
        self.lives = self.config["lives"]
        self.level_index = 0
        if self._build_level(self.level_index):
            self.state = State.PLAYING
        else:
            self.state = State.MENU

    def _restart_current_level(self, lose_life: bool) -> None:
        """Rebuild the current level, optionally costing the player a life."""
        if lose_life:
            self.lives -= 1
        if self.lives <= 0:
            self._end_game(victory=False)
            return
        if not self._build_level(self.level_index):
            self._end_game(victory=False)

    def _advance_level(self) -> None:
        """Move to the next level, or win the game if none remain."""
        self.level_index += 1
        if self.level_index >= len(self.config["levels"]):
            self._end_game(victory=True)
            return
        if not self._build_level(self.level_index):
            self._end_game(victory=True)

    def _end_game(self, victory: bool) -> None:
        """Transition to the name-entry screen after a win or loss."""
        self.victory = victory
        self.name_input = ""
        self.state = State.ENTER_NAME

    # ------------------------------------------------------------------
    # Update logic
    # ------------------------------------------------------------------
    def _update_playing(self, dt: float) -> None:
        assert self.level is not None and self.player is not None
        walls = self.level.walls

        self.time_left -= dt
        if self.time_left <= 0:
            self._restart_current_level(lose_life=True)
            return

        self.player_move_timer += dt
        move_interval = PLAYER_MOVE_INTERVAL / max(self.speed_multiplier, 0.1)
        if self.player_move_timer >= move_interval:
            self.player_move_timer = 0.0
            self.player.step(walls)
            self._handle_collectibles()
            self._handle_ghost_collisions()

        if not self.ghosts_frozen:
            self.ghost_move_timer += dt
            if self.ghost_move_timer >= GHOST_MOVE_INTERVAL:
                self.ghost_move_timer = 0.0
                for ghost in self.level.ghosts:
                    ghost.step(walls, (self.player.x, self.player.y), self.rng)
                self._handle_ghost_collisions()

        for ghost in self.level.ghosts:
            ghost.update_timers(dt)

        if not self.level.pacgums and not self.level.super_pacgums:
            self._advance_level()

    def _handle_collectibles(self) -> None:
        assert self.level is not None and self.player is not None
        pos = (self.player.x, self.player.y)
        if pos in self.level.pacgums:
            self.level.pacgums.discard(pos)
            self.score += self.config["points_per_pacgum"]
        elif pos in self.level.super_pacgums:
            self.level.super_pacgums.discard(pos)
            self.score += self.config["points_per_super_pacgum"]
            for ghost in self.level.ghosts:
                ghost.make_edible(EDIBLE_DURATION)

    def _handle_ghost_collisions(self) -> None:
        assert self.level is not None and self.player is not None
        for ghost in self.level.ghosts:
            if (ghost.x, ghost.y) != (self.player.x, self.player.y):
                continue
            if ghost.state == GhostState.EDIBLE:
                ghost.get_eaten(GHOST_RESPAWN_DELAY)
                self.score += self.config["points_per_ghost"]
            elif ghost.state == GhostState.CHASE and not self.invincible:
                self._restart_current_level(lose_life=True)
                return

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.state = State.QUIT
            return
        if event.type != pygame.KEYDOWN:
            return

        if self.state == State.MENU:
            self._handle_menu_key(event.key)
        elif self.state == State.INSTRUCTIONS:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.state = State.MENU
        elif self.state == State.PLAYING:
            self._handle_playing_key(event.key)
        elif self.state == State.PAUSED:
            self._handle_pause_key(event.key)
        elif self.state == State.ENTER_NAME:
            self._handle_name_key(event)

    def _handle_menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_selected = (self.menu_selected - 1) % 3
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_selected = (self.menu_selected + 1) % 3
        elif key == pygame.K_RETURN:
            if self.menu_selected == 0:
                self.start_new_game()
            elif self.menu_selected == 1:
                self.state = State.INSTRUCTIONS
            else:
                self.state = State.QUIT

    def _handle_playing_key(self, key: int) -> None:
        assert self.player is not None
        if key in _KEY_DIRECTIONS:
            self.player.set_direction(_KEY_DIRECTIONS[key])
        elif key == pygame.K_p:
            self.pause_selected = 0
            self.state = State.PAUSED
        elif key == pygame.K_c:
            self.cheat_mode = not self.cheat_mode
        elif self.cheat_mode:
            self._handle_cheat_key(key)

    def _handle_cheat_key(self, key: int) -> None:
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

    def _handle_pause_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.pause_selected = 1 - self.pause_selected
        elif key == pygame.K_RETURN:
            if self.pause_selected == 0:
                self.state = State.PLAYING
            else:
                self.state = State.MENU
        elif key == pygame.K_p:
            self.state = State.PLAYING

    def _handle_name_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_RETURN:
            self.highscores.add_score(self.name_input or "Player", self.score)
            self.state = State.VICTORY if self.victory else State.GAME_OVER
        elif event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
        elif event.unicode.isalnum() or event.unicode == " ":
            if len(self.name_input) < 10:
                self.name_input += event.unicode

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render_playing(self) -> None:
        assert self.level is not None and self.player is not None
        self.screen.fill(COLOR_BG)
        for y, row in enumerate(self.level.walls):
            for x, is_wall in enumerate(row):
                if is_wall:
                    rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(self.screen, COLOR_WALL, rect, border_radius=3)

        for (x, y) in self.level.pacgums:
            center = (x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2)
            pygame.draw.circle(self.screen, COLOR_PACGUM, center, 3)
        for (x, y) in self.level.super_pacgums:
            center = (x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2)
            pygame.draw.circle(self.screen, COLOR_SUPER_PACGUM, center, 7)

        for ghost in self.level.ghosts:
            center = (ghost.x * CELL_SIZE + CELL_SIZE // 2, ghost.y * CELL_SIZE + CELL_SIZE // 2)
            color = GHOST_EDIBLE_COLOR if ghost.state == GhostState.EDIBLE else ghost.color
            if ghost.state == GhostState.EATEN:
                pygame.draw.circle(self.screen, color, center, CELL_SIZE // 2 - 8, width=2)
            else:
                pygame.draw.circle(self.screen, color, center, CELL_SIZE // 2 - 3)

        pcenter = (self.player.x * CELL_SIZE + CELL_SIZE // 2,
                   self.player.y * CELL_SIZE + CELL_SIZE // 2)
        pygame.draw.circle(self.screen, COLOR_PLAYER, pcenter, CELL_SIZE // 2 - 2)

        ui.draw_hud(self.screen, self.small_font, self.score, self.lives,
                    self.level_index + 1, max(self.time_left, 0), self.cheat_mode)

    def _render(self) -> None:
        if self.state == State.MENU:
            ui.draw_main_menu(self.screen, self.title_font, self.font, self.small_font,
                               self.highscores.top(), self.menu_selected)
        elif self.state == State.INSTRUCTIONS:
            ui.draw_instructions(self.screen, self.font, self.small_font)
        elif self.state in (State.PLAYING, State.PAUSED):
            self._render_playing()
            if self.state == State.PAUSED:
                ui.draw_pause_menu(self.screen, self.font, self.pause_selected)
        elif self.state == State.ENTER_NAME:
            ui.draw_end_screen(self.screen, self.title_font, self.font,
                                self.victory, self.score, self.name_input)
        elif self.state in (State.GAME_OVER, State.VICTORY):
            ui.draw_end_screen(self.screen, self.title_font, self.font,
                                self.state == State.VICTORY, self.score, self.name_input)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the game loop until the player quits."""
        try:
            while self.state != State.QUIT:
                dt = self.clock.tick(FPS) / 1000.0

                for event in pygame.event.get():
                    self._handle_event(event)
                    if event.type == pygame.KEYDOWN and self.state in (
                        State.GAME_OVER, State.VICTORY
                    ) and event.key == pygame.K_RETURN:
                        self.state = State.MENU

                if self.state == State.PLAYING:
                    self._update_playing(dt)

                self._render()
        except Exception as exc:  # pragma: no cover - last-resort safety net
            print(f"[game] Unexpected error, shutting down cleanly: {exc}")
        finally:
            pygame.quit()