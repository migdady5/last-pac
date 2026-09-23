"""Rendering helpers for menus, HUD and overlay screens."""
from __future__ import annotations

from typing import List, Tuple

import pygame

from src.constants import COLOR_HIGHLIGHT, COLOR_TEXT
from src.highscore import HighscoreEntry


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
              center: Tuple[int, int], color: Tuple[int, int, int] = COLOR_TEXT) -> None:
    """Render centered text at a given position.

    Args:
        surface: Target drawing surface.
        font: Font used to render the text.
        text: The string to draw.
        center: (x, y) pixel coordinates for the text's center.
        color: RGB text color.
    """
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


def draw_main_menu(surface: pygame.Surface, title_font: pygame.font.Font,
                    font: pygame.font.Font, small_font: pygame.font.Font,
                    highscores: List[HighscoreEntry], selected: int) -> None:
    """Draw the main menu with title, options and highscore list."""
    surface.fill((0, 0, 0))
    width, height = surface.get_size()
    draw_text(surface, title_font, "PAC-MAN", (width // 2, 70), (255, 255, 0))

    options = ["Start Game", "Instructions", "Exit"]
    for index, option in enumerate(options):
        color = COLOR_HIGHLIGHT if index == selected else COLOR_TEXT
        prefix = "> " if index == selected else "  "
        draw_text(surface, font, f"{prefix}{option}", (width // 2, 150 + index * 36), color)

    draw_text(surface, font, "Highscores", (width // 2, 270), (255, 255, 0))
    if not highscores:
        draw_text(surface, small_font, "No scores yet", (width // 2, 300))
    for index, entry in enumerate(highscores[:10]):
        line = f"{index + 1}. {entry['name']} - {entry['score']} pts"
        draw_text(surface, small_font, line, (width // 2, 300 + index * 22))


def draw_instructions(surface: pygame.Surface, font: pygame.font.Font,
                       small_font: pygame.font.Font) -> None:
    """Draw the instructions / controls screen."""
    surface.fill((0, 0, 0))
    width, _ = surface.get_size()
    draw_text(surface, font, "Instructions", (width // 2, 60), (255, 255, 0))
    lines = [
        "Arrow keys or WASD: move",
        "P: pause / resume",
        "ENTER: confirm / continue",
        "Eat all pacgums to clear a level.",
        "Super-pacgums (corners) let you eat ghosts briefly.",
        "Avoid ghosts unless they're edible (blue).",
        "",
        "Cheat mode (press C to toggle):",
        "  I: invincibility   F: freeze ghosts",
        "  L: extra life      K: skip level",
        "  +/-: player speed",
        "",
        "Press ENTER or ESC to go back",
    ]
    for index, line in enumerate(lines):
        draw_text(surface, small_font, line, (width // 2, 110 + index * 24))


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, score: int, lives: int,
             level_number: int, time_left: float, cheat_active: bool) -> None:
    """Draw the always-visible in-game heads-up display."""
    width, height = surface.get_size()
    hud_y = height - 26
    text = f"Score: {score}   Lives: {lives}   Level: {level_number}   Time: {int(time_left)}"
    if cheat_active:
        text += "   [CHEAT MODE]"
    draw_text(surface, font, text, (width // 2, hud_y))


def draw_pause_menu(surface: pygame.Surface, font: pygame.font.Font, selected: int) -> None:
    """Draw a translucent pause overlay with Resume / Main Menu options."""
    width, height = surface.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    draw_text(surface, font, "PAUSED", (width // 2, height // 2 - 50), (255, 255, 0))
    options = ["Resume", "Return to Main Menu"]
    for index, option in enumerate(options):
        color = COLOR_HIGHLIGHT if index == selected else COLOR_TEXT
        prefix = "> " if index == selected else "  "
        draw_text(surface, font, f"{prefix}{option}", (width // 2, height // 2 + index * 34))


def draw_end_screen(surface: pygame.Surface, title_font: pygame.font.Font,
                     font: pygame.font.Font, victory: bool, score: int,
                     name_input: str) -> None:
    """Draw the game-over or victory screen with a name entry prompt."""
    surface.fill((0, 0, 0))
    width, height = surface.get_size()
    title = "YOU WIN!" if victory else "GAME OVER"
    color = (0, 255, 0) if victory else (255, 60, 60)
    draw_text(surface, title_font, title, (width // 2, height // 2 - 90), color)
    draw_text(surface, font, f"Final score: {score}", (width // 2, height // 2 - 40))
    draw_text(surface, font, "Enter your name:", (width // 2, height // 2 + 10))
    draw_text(surface, font, f"[{name_input}_]", (width // 2, height // 2 + 44),
              COLOR_HIGHLIGHT)
    draw_text(surface, font, "Press ENTER to confirm", (width // 2, height // 2 + 90))