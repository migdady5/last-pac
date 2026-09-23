import pygame

from srcs.entity import Entity



class Player(Entity):
    """
    Pacman player.
    """


    def __init__(self,x:int,y:int)->None:

        super().__init__(x,y)

        self.speed = 4



    def move(self, keys, maze)->None:

        new_x = self.x
        new_y = self.y


        if keys[pygame.K_LEFT] or keys[pygame.K_a]:

            new_x -= self.speed


        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:

            new_x += self.speed


        if keys[pygame.K_UP] or keys[pygame.K_w]:

            new_y -= self.speed


        if keys[pygame.K_DOWN] or keys[pygame.K_s]:

            new_y += self.speed



        if not maze.is_wall(new_x,new_y):

            self.x = new_x
            self.y = new_y