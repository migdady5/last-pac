import sys

from srcs.config import Config
from srcs.game import Game



def main()->None:


    if len(sys.argv)!=2:

        print(
            "Usage: python pac-man.py config.json"
        )

        return



    config = Config(
        sys.argv[1]
    )


    game = Game(
        config
    )


    game.run()



if __name__=="__main__":

    main()