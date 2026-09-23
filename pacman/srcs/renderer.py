import pygame


class Renderer:

    def __init__(self):

        pygame.init()

        self.screen = pygame.display.set_mode(
            (800,600)
        )

        pygame.display.set_caption(
            "Pacman"
        )

        self.images = {}

        self.load_images()


    def load_images(self):

        self.images["pacman"] = pygame.image.load(
            "assets/images/characters/open.png"
        )

        self.images["wall"] = pygame.image.load(
            "assets/images/walls/top.png"
        )

        self.images["blue"] = pygame.image.load(
            "assets/images/characters/blue_right.png"
        )

        self.images["green"] = pygame.image.load(
            "assets/images/characters/green_right.png"
        )

        self.images["orange"] = pygame.image.load(
            "assets/images/characters/orange_right.png"
        )

        self.images["purple"] = pygame.image.load(
            "assets/images/characters/purple_right.png"
        )


    def clear(self) -> None:
        self.screen.fill((0, 0, 0))

    def draw_wall(self, x: int, y: int) -> None:
        self.screen.blit(
            self.images["wall"],
            (x, y)
        )

    def draw_pacman(self, x: int, y: int) -> None:
        self.screen.blit(
            self.images["pacman"],
            (x, y)
        )

    def draw_ghost(self, color: str, x: int, y: int) -> None:
        self.screen.blit(
            self.images[color],
            (x, y)
        )

    def update(self) -> None:
        pygame.display.flip()