# brickbreaker

Procedural brick-breaker — deterministic frame simulation, seeded
level generator, power-ups and unicode rendering. Pure standard
library, no asset files, no wall-clock: every frame is computed, so
the whole game is unit-testable.

```text
$ python3 -m brickbreaker.cli --level 3 --seed 11
+------------------------------+
|         ▤▤▤  ▤▤              |
|      ▤▤▤▤▤   ▤▤▤             |
...
|              ▬               |
+------------------------------+
```

## The pieces

- **Level generator** — 5 symmetric patterns (checker, pyramid,
  stripes, fortress, random) with scaling difficulty: more rows every
  other level, bricks gain hits every 3 levels, ~12% carry power-ups.
  Deterministic per (level, seed).
- **Physics** — swept circle-vs-rect collision (slab method) so fast
  balls never tunnel through bricks; AABB reflection resolves along the
  shallowest penetration axis; sub-stepping handles up to 4 collisions
  per frame.
- **Paddle** — bounce angle depends on the hit point: edge hits fly
  steep, center hits fly straight up.
- **Power-ups** — broken bricks drop `expand` (wider paddle) and
  `slow` (slower ball) tokens that fall; catching them applies the
  effect.
- **Floor sweep** — the ball is resolved exactly at the floor line and
  a life is lost; 3 lives, then game over.

## CLI

```
python3 -m brickbreaker.cli [--level N] [--seed N] [--headless]
```

`--headless` simulates without rendering (used by the test suite).

## Development

```console
$ python3 -m unittest discover -s tests   # 15 tests: physics sweep,
                                          # reflections, levels, session
```

## License

MIT — see [LICENSE](LICENSE).
