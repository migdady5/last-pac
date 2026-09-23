class Maze:
    """
    Handles the game maze.
    """


    def __init__(self) -> None:

        self.tile_size = 32


        self.map = [
            "########################",
            "#......................#",
            "#.####.########.####...#",
            "#......................#",
            "#.####.##....##.####...#",
            "#......##....##........#",
            "#.####.########.####...#",
            "#......................#",
            "########################"
        ]



    def is_wall(self, x: int, y: int) -> bool:
        """
        Check if position contains a wall.
        """

        row = y // self.tile_size
        col = x // self.tile_size


        if row < 0 or row >= len(self.map):
            return True


        if col < 0 or col >= len(self.map[row]):
            return True


        return self.map[row][col] == "#"



    def draw(self, renderer) -> None:
        """
        Draw maze.
        """
    
        for row_index, row in enumerate(self.map):
        
            for col_index, tile in enumerate(row):
            
                if tile == "#":
                
                    renderer.draw_wall(
                        col_index * self.tile_size,
                        row_index * self.tile_size
                    )