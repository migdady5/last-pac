import pygame

from srcs.renderer import Renderer
from srcs.maze import Maze
from srcs.player import Player
from srcs.ghost import Ghost



class Game:
    """
    Main game controller.
    """


    def __init__(self,config)->None:

        self.config = config

        self.running = True


        self.renderer = Renderer()

        self.maze = Maze()


        self.player = Player(
            64,
            64
        )

        self.ghosts = [

        Ghost(320,160,"blue"),

        Ghost(360,160,"green"),

        Ghost(400,160,"orange"),

        Ghost(440,160,"purple")

    ]



    def run(self)->None:


        clock = pygame.time.Clock()


        while self.running:


            self.events()


            self.update()


            self.draw()


            clock.tick(60)



    def events(self)->None:


        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                self.running=False



    def update(self)->None:


        keys = pygame.key.get_pressed()


        self.player.move(
            keys,
            self.maze
        )

        for ghost in self.ghosts:

            ghost.move(
                self.maze
            )



    def draw(self)->None:


        self.renderer.clear()


        self.maze.draw(
            self.renderer
        )


        x,y = self.player.get_position()


        self.renderer.draw_pacman(
            x,
            y
        )


        self.renderer.update()

        for ghost in self.ghosts:

            x,y = ghost.get_position()
        
            self.renderer.draw_ghost(
                ghost.color,
                x,
                y
            )