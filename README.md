# Pacman

A Python Pacman game built for the 42 project.

## Run

```bash
python pac-man.py config.json
```

## Checks

```bash
flake8 src
mypy src
```

## Structure

- `src/` game logic
- `assets/` resources
- `maze_ing` external maze generator adapter

## Notes

The project uses an adapter layer for the external maze package and keeps gameplay logic independent from maze generation.
