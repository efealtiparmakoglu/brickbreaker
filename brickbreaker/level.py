"""Procedural level generation: symmetric brick patterns from a seed."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .physics import Brick


@dataclass
class LevelSpec:
    number: int
    cols: int
    rows: int
    brick_width: float
    brick_height: float
    seed: int
    pattern: str
    bricks: list[Brick] = field(default_factory=list)


PATTERNS = ["checker", "pyramid", "stripes", "random", "fortress"]


def generate_level(number: int, seed: int = 0) -> LevelSpec:
    """Build level `number` (1-based). Higher levels: more rows, tougher
    bricks (multi-hit), denser patterns. Deterministic per (number, seed)."""
    rng = random.Random(seed * 1_000_003 + number * 7 + 1)
    cols = 7
    rows = min(4 + number // 2, 8)
    spec = LevelSpec(
        number=number,
        cols=cols,
        rows=rows,
        brick_width=8.2,
        brick_height=2.0,
        seed=seed,
        pattern=PATTERNS[number % len(PATTERNS)],
    )
    spec_bricks: list[Brick] = []
    left_margin = 1.2
    top_margin = 4.0

    def brick_at(col: int, row: int) -> Brick:
        hits = 1 + (number - 1) // 3  # tougher every 3 levels
        hits = min(hits, 3)
        carries = rng.random() < 0.12  # ~12% of bricks carry a power-up
        return Brick(
            x=left_margin + col * spec.brick_width,
            y=top_margin + row * spec.brick_height,
            width=spec.brick_width - 0.2,
            height=spec.brick_height - 0.2,
            hits=hits,
            power=("expand" if carries else None),
        )

    for row in range(rows):
        for col in range(cols):
            keep = False
            if spec.pattern == "checker":
                keep = (row + col) % 2 == 0
            elif spec.pattern == "pyramid":
                half = cols / 2
                keep = abs(col - (half - 0.5)) <= row + 1.5
            elif spec.pattern == "stripes":
                keep = row % 2 == 0 or col % 3 == 0
            elif spec.pattern == "fortress":
                border = row in (0, rows - 1) or col in (0, cols - 1)
                keep = border or (row + col) % 4 == 0
            else:  # random
                keep = rng.random() < 0.75
            if keep:
                spec_bricks.append(brick_at(col, row))

    spec.bricks = spec_bricks
    return spec
