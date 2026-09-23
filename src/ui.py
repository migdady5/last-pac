"""Rendering helpers for menus, HUD and overlay screens."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

from src.constants import COLOR_HIGHLIGHT, COLOR_TEXT
from src.highscore import HighscoreEntry


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    center: tuple[int, int],
    color: tuple[int, int, int] = COLOR_TEXT,
) -> None:
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


@lru_cache(maxsize=4)
def _menu_background(width: int, height: int) -> pygame.Surface:
    """Build a static arcade background once per window size."""
    background = pygame.Surface((width, height))
    background.fill((3, 5, 14))
    unit = max(1, min(width, height) / 694)

    def point(x: float, y: float) -> tuple[int, int]:
        return round(width * x), round(height * y)

    border = pygame.Rect(14, 14, width - 28, height - 28)
    for thickness, color in ((9, (4, 18, 50)), (3, (15, 95, 220))):
        pygame.draw.rect(background, color, border, thickness,
                         border_radius=20)
    # Symmetrical maze-like tracks around the outer margins.
    for mirror in (False, True):
        for track in (
            ((.08,.12),(.16,.12),(.16,.22),(.10,.22),(.10,.34)),
            ((.07,.42),(.14,.42),(.14,.58),(.08,.58),(.08,.68)),
            ((.08,.78),(.08,.89),(.23,.89),(.23,.94)),
        ):
            pts = [point(1-x if mirror else x, y) for x,y in track]
            pygame.draw.lines(background, (8, 28, 70), False, pts, 8)
            pygame.draw.lines(background, (20, 115, 225), False, pts, 2)
    for fraction in (.055, .945):
        for i in range(16):
            pygame.draw.circle(background, (200, 174, 89),
                               point(fraction, .16 + i * .042), 2)
    # A quiet central panel keeps title and selectable text readable.
    panel = pygame.Rect(round(width*.21), round(height*.08),
                        round(width*.58), round(height*.59))
    pygame.draw.rect(background, (5, 9, 22), panel, border_radius=24)
    pygame.draw.rect(background, (19, 40, 76), panel, 1, border_radius=24)
    pygame.draw.line(background, (22, 65, 110),
                     point(.32,.25), point(.68,.25), 1)

    # Use the exact existing game characters, with no new image downloads.
    directory = Path(__file__).resolve().parent.parent / 'assets/images/characters'
    characters = ('blue_right.png', 'green_right.png', 'orange_right.png',
                  'purple_right.png', 'open.png')
    size = round(38 * unit)
    for index, filename in enumerate(characters):
        path = directory / filename
        if path.is_file():
            sprite = pygame.image.load(str(path)).convert_alpha()
            sprite = pygame.transform.smoothscale(sprite, (size, size))
            center = point(.27 + index * .095, .78)
            background.blit(sprite, sprite.get_rect(center=center))
    for fraction in (.72, .77, .82):
        pygame.draw.circle(background, (255, 224, 145),
                           point(fraction, .78), max(2, round(3*unit)))
    return background


def draw_main_menu(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    highscores: list[HighscoreEntry],
    selected: int,
) -> None:
    """Draw a static arcade menu with keyboard selection and live scores."""
    width, height = surface.get_size()
    surface.blit(_menu_background(width, height), (0, 0))
    draw_text(surface, title_font, 'PAC-MAN',
              (width // 2, round(height * .16)), (255, 225, 30))
    options = ['Start Game', 'View Highscores', 'Instructions', 'Exit']
    spacing = max(36, round(height * .057))
    first_y = round(height * .32)
    for index, option in enumerate(options):
        y = first_y + index * spacing
        if index == selected:
            rect = pygame.Rect(0, 0, round(width*.47), spacing - 5)
            rect.center = (width//2, y)
            pygame.draw.rect(surface, (8, 43, 61), rect, border_radius=8)
            pygame.draw.rect(surface, (0, 173, 199), rect, 1, border_radius=8)
        color = COLOR_HIGHLIGHT if index == selected else COLOR_TEXT
        prefix = '> ' if index == selected else '  '
        draw_text(surface, font, prefix + option, (width//2, y), color)
    best = highscores[0] if highscores else None
    best_text = f"Best: {best['name']} - {best['score']} pts" if best else 'No scores yet'
    draw_text(surface, small_font, best_text,
              (width//2, round(height*.59)), (162, 179, 202))
    draw_text(surface, small_font, 'ARROWS: SELECT   ENTER: CONFIRM',
              (width//2, round(height*.91)), (162, 179, 202))


def draw_highscores(
    surface: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    highscores: list[HighscoreEntry],
) -> None:
    """Draw the dedicated top-ten highscore screen."""
    surface.fill((0, 0, 0))
    width, _ = surface.get_size()
    draw_text(surface, font, "TOP 10 HIGHSCORES", (width // 2, 55), (255, 255, 0))
    if not highscores:
        draw_text(surface, small_font, "No scores yet", (width // 2, 115))
    for index, entry in enumerate(highscores[:10]):
        line = f"{index + 1:>2}. {entry['name']:<10} {entry['score']:>8} pts"
        draw_text(surface, small_font, line, (width // 2, 105 + index * 28))
    draw_text(surface, small_font, "Press ENTER or ESC to return", (width // 2, 410))


def draw_instructions(
    surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font
) -> None:
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


def draw_hud(
    surface: pygame.Surface,
    font: pygame.font.Font,
    score: int,
    lives: int,
    level_number: int,
    time_left: float,
    cheat_active: bool,
) -> None:
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
        draw_text(
            surface,
            font,
            f"{prefix}{option}",
            (width // 2, height // 2 + index * 34),
            color,
        )


def draw_end_screen(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    font: pygame.font.Font,
    victory: bool,
    score: int,
    name_input: str,
) -> None:
    """Draw the game-over or victory screen with a name entry prompt."""
    surface.fill((0, 0, 0))
    width, height = surface.get_size()
    title = "YOU WIN!" if victory else "GAME OVER"
    color = (0, 255, 0) if victory else (255, 60, 60)
    draw_text(surface, title_font, title, (width // 2, height // 2 - 90), color)
    draw_text(surface, font, f"Final score: {score}", (width // 2, height // 2 - 40))
    draw_text(surface, font, "Enter your name:", (width // 2, height // 2 + 10))
    draw_text(surface, font, f"[{name_input}_]", (width // 2, height // 2 + 44), COLOR_HIGHLIGHT)
    draw_text(surface, font, "Press ENTER to confirm", (width // 2, height // 2 + 90))