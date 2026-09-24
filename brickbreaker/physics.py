"""Physics: vectors, circle-rect ball collisions and reflections."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Vec:
    x: float
    y: float

    def add(self, other: "Vec") -> "Vec":
        return Vec(self.x + other.x, self.y + other.y)

    def scaled(self, factor: float) -> "Vec":
        return Vec(self.x * factor, self.y * factor)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec":
        length = self.length()
        if length == 0:
            return Vec(0.0, 0.0)
        return Vec(self.x / length, self.y / length)


@dataclass
class Ball:
    pos: Vec
    vel: Vec
    radius: float = 0.4


@dataclass
class Paddle:
    x: float
    width: float = 6.0
    y: float = 0.0  # the paddle line


@dataclass
class Brick:
    x: float
    y: float
    width: float
    height: float
    hits: int = 1  # remaining hits before it breaks
    power: str | None = None  # set when the brick carries a power-up

    @property
    def alive(self) -> bool:
        return self.hits > 0


def reflect_off_rect(ball: Ball, rect: tuple[float, float, float, float]) -> Vec:
    """Reflect the ball velocity off an axis-aligned rect and return the
    dominant collision normal (unit vector). Simple AABB resolution:
    push the ball out along the shallowest penetration axis and flip the
    matching velocity component."""
    rx, ry, rw, rh = rect
    ball_x, ball_y = ball.pos.x, ball.pos.y
    # closest point on the rect to the ball center
    closest_x = min(max(ball_x, rx), rx + rw)
    closest_y = min(max(ball_y, ry), ry + rh)
    dx = ball_x - closest_x
    dy = ball_y - closest_y
    if dx == 0 and dy == 0:
        # center inside the rect: escape along the smallest exit distance
        left = ball_x - rx
        right = rx + rw - ball_x
        top = ball_y - ry
        bottom = ry + rh - ball_y
        minimum = min(left, right, top, bottom)
        if minimum == left:
            normal = Vec(-1.0, 0.0)
            ball.pos.x = rx - ball.radius
        elif minimum == right:
            normal = Vec(1.0, 0.0)
            ball.pos.x = rx + rw + ball.radius
        elif minimum == top:
            normal = Vec(0.0, -1.0)
            ball.pos.y = ry - ball.radius
        else:
            normal = Vec(0.0, 1.0)
            ball.pos.y = ry + rh + ball.radius
    elif abs(dx) >= abs(dy):
        normal = Vec(math.copysign(1.0, dx), 0.0)
        ball.pos.x = closest_x + normal.x * ball.radius
    else:
        normal = Vec(0.0, math.copysign(1.0, dy))
        ball.pos.y = closest_y + normal.y * ball.radius
    # reflect the velocity across the normal
    dot = ball.vel.x * normal.x + ball.vel.y * normal.y
    ball.vel = Vec(
        ball.vel.x - 2 * dot * normal.x,
        ball.vel.y - 2 * dot * normal.y,
    )
    return normal


def moving_circle_hits_rect(
    pos: Vec, delta: Vec, radius: float, rect: tuple[float, float, float, float]
) -> float | None:
    """Continuous collision: return the hit fraction t in [0, 1] when the
    moving circle sweeps into the rect during this step, else None.
    Conservative test: sample the swept path via the closest-approach
    distance between the segment and the inflated rect."""
    rx, ry, rw, rh = rect
    # inflate the rect by the radius and test segment-rect intersection
    ix, iy, iw, ih = rx - radius, ry - radius, rw + 2 * radius, rh + 2 * radius
    start_x, start_y = pos.x, pos.y
    end_x, end_y = pos.x + delta.x, pos.y + delta.y
    lo_t, hi_t = 0.0, 1.0
    # slab method per axis
    ok = True
    for axis in (0, 1):
        s = (start_x, start_y)[axis]
        e = (end_x, end_y)[axis]
        lo = (ix, iy)[axis]
        hi = lo + (iw, ih)[axis]
        d = e - s
        if abs(d) < 1e-12:
            if s < lo or s > hi:
                ok = False
                break
        else:
            t0 = (lo - s) / d
            t1 = (hi - s) / d
            if t0 > t1:
                t0, t1 = t1, t0
            lo_t = max(lo_t, t0)
            hi_t = min(hi_t, t1)
            if lo_t > hi_t:
                ok = False
                break
    if not ok or lo_t > 1.0:
        return None
    return max(lo_t, 0.0)
