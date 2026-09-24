"""Procedural brick-breaker: level generator, physics, power-ups.

The simulation is deterministic and frame-based (no wall-clock), so the
whole game is unit-testable: aim the ball, simulate frames, verify
physics and level generation properties.
"""

from .physics import Vec, Ball, Paddle, Brick, reflect_off_rect, moving_circle_hits_rect
from .level import LevelSpec, generate_level
from .game import GameSession, PowerUp

__version__ = "1.0.0"

__all__ = [
    "Vec", "Ball", "Paddle", "Brick", "reflect_off_rect", "moving_circle_hits_rect",
    "LevelSpec", "generate_level", "GameSession", "PowerUp",
]
