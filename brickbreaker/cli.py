"""CLI: simulate a level headlessly (deterministic demo)."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .game import GameSession


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-V", "--version", action="store_true")
    args = parser.parse_args(argv)

    if args.help:
        print("brickbreaker v%s — procedural brick-breaker" % __version__)
        print("USAGE: brickbreaker --level N --seed N [--headless]")
        return
    if args.version:
        print("brickbreaker", __version__)
        return

    game = GameSession(level_number=max(1, args.level), seed=args.seed)
    if args.headless:
        # deterministic AI: paddle follows the ball's x each frame
        for _ in range(1200):
            game.move_paddle_to(game.ball.pos.x - game.paddle.width / 2)
            game.step_frame()
            if game.lost or game.won:
                break
        print(game.render())
        print(f"level {game.level_number}: score {game.score}, "
              f"lives {game.lives}, {'WON' if game.won else 'lost' if game.lost else 'running'}")
        return
    print(game.render())
    print("interactive play needs a real terminal; use --headless for the demo")


if __name__ == "__main__":
    main(sys.argv[1:])
