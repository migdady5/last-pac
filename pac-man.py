"""Command-line entry point for the Pac-Man game."""

import sys

from src.config import load_config
from src.game import Game


def main() -> int:
    """Load the requested configuration and run the game."""
    if len(sys.argv) != 2:
        print("Usage: python pac-man.py config.json")
        return 1

    try:
        config = load_config(sys.argv[1])
        game = Game(config)
        game.run()
    except Exception as error:
        print(f"Error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
