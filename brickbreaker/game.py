"""Game session: deterministic frame simulation of ball, paddle, bricks,
power-ups, walls and the lose condition. Rendering (unicode) is here too
so headless tests can see the board."""

from __future__ import annotations

from dataclasses import dataclass, field

from .level import generate_level
from .physics import Ball, Brick, Paddle, Vec, moving_circle_hits_rect, reflect_off_rect

FIELD_W = 60.0
FIELD_H = 40.0

POWER_UP_KINDS = ("expand", "slow", "multi")


@dataclass
class PowerUp:
    x: float
    y: float
    kind: str


@dataclass
class GameSession:
    level_number: int
    seed: int = 0
    paddle_width: float = 7.0

    def __post_init__(self) -> None:
        self.spec = generate_level(self.level_number, self.seed)
        self.bricks: list[Brick] = list(self.spec.bricks)
        self.paddle = Paddle(x=FIELD_W / 2 - self.paddle_width / 2,
                             width=self.paddle_width, y=FIELD_H - 2.0)
        launch_angle = -1.0  # up and slightly right
        self.ball = Ball(pos=Vec(FIELD_W / 2, FIELD_H - 3.0),
                         vel=Vec(launch_angle, -2.0).normalized().scaled(30.0))
        self.score = 0
        self.lives = 3
        self.frame = 0
        self.lost = False
        self.won = False
        self.power_ups: list[PowerUp] = []
        self.events: list[str] = []

    # --- input -------------------------------------------------------------

    def move_paddle_to(self, x: float) -> None:
        self.paddle.x = min(max(x, 0.0), FIELD_W - self.paddle.width)

    # --- simulation --------------------------------------------------------

    def step_frame(self) -> None:
        if self.lost or self.won:
            return
        self.frame += 1
        ball = self.ball
        delta = ball.vel.scaled(1.0 / 30.0)  # one frame at 30 fps
        remaining = 1.0
        for _ in range(4):  # up to 4 sub-collision events per frame
            hit_t = self._first_hit(ball, delta.scaled(remaining))
            if hit_t is None:
                ball.pos = ball.pos.add(delta.scaled(remaining))
                break
            ball.pos = ball.pos.add(delta.scaled(hit_t))
            remaining -= hit_t
            event = self._resolve(ball)
            if event:
                self.events.append(event)
            if self.lost or self.won:
                return
        # falling power-ups
        for pu in list(self.power_ups):
            pu.y += 0.25
            if pu.y >= self.paddle.y and self.paddle.x <= pu.x <= self.paddle.x + self.paddle.width:
                self.power_ups.remove(pu)
                self.events.append(f"power:{pu.kind}")
                if pu.kind == "expand":
                    self.paddle.width = min(self.paddle.width + 2.0, 12.0)
                elif pu.kind == "slow":
                    self.ball.vel = self.ball.vel.scaled(0.8)
            elif pu.y > FIELD_H:
                self.power_ups.remove(pu)

    def _first_hit(self, ball: Ball, delta: Vec) -> float | None:
        candidates: list[tuple[float, str, int]] = []
        # walls
        if ball.pos.x - ball.radius + min(delta.x, 0) <= 0:
            t = (ball.radius - ball.pos.x) / delta.x if delta.x < 0 else 0.0
            candidates.append((max(t, 0.0), "wall-left", -1))
        if ball.pos.x + ball.radius + max(delta.x, 0) >= FIELD_W:
            t = (FIELD_W - ball.radius - ball.pos.x) / delta.x if delta.x > 0 else 0.0
            candidates.append((max(t, 0.0), "wall-right", -1))
        if ball.pos.y - ball.radius + min(delta.y, 0) <= 0:
            t = (ball.radius - ball.pos.y) / delta.y if delta.y < 0 else 0.0
            candidates.append((max(t, 0.0), "wall-top", -1))
        if ball.pos.y - ball.radius >= FIELD_H:
            candidates.append((0.0, "floor", -1))
        elif delta.y > 0 and ball.pos.y + ball.radius < FIELD_H:
            reach = FIELD_H - ball.radius - ball.pos.y
            if delta.y >= reach:
                candidates.append((max(reach / delta.y, 0.0), "floor", -1))
        # paddle: only when moving down
        if delta.y > 0:
            pad_rect = (self.paddle.x, self.paddle.y, self.paddle.width, 1.0)
            t = moving_circle_hits_rect(ball.pos, delta, ball.radius, pad_rect)
            if t is not None:
                candidates.append((t, "paddle", -1))
        # bricks
        for i, brick in enumerate(self.bricks):
            if not brick.alive:
                continue
            rect = (brick.x, brick.y, brick.width, brick.height)
            t = moving_circle_hits_rect(ball.pos, delta, ball.radius, rect)
            if t is not None:
                candidates.append((t, "brick", i))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        best_t, kind, index = candidates[0]
        self._pending_hit = (kind, index)
        return best_t

    def _resolve(self, ball: Ball) -> str | None:
        kind, index = self._pending_hit
        if kind == "wall-left" or kind == "wall-right":
            ball.vel = Vec(-ball.vel.x, ball.vel.y)
            ball.pos.x = min(max(ball.pos.x, ball.radius), FIELD_W - ball.radius)
            return None
        if kind == "wall-top":
            ball.vel = Vec(ball.vel.x, -ball.vel.y)
            ball.pos.y = max(ball.pos.y, ball.radius)
            return None
        if kind == "floor":
            self.lives -= 1
            if self.lives <= 0:
                self.lost = True
            else:
                self.ball = Ball(pos=Vec(FIELD_W / 2, FIELD_H - 3.0),
                                 vel=Vec(-1.0, -2.0).normalized().scaled(30.0))
            return "lost-ball"
        if kind == "paddle":
            # the bounce angle depends on where the ball hit the paddle:
            # edge hits fly steep, center hits fly straight up
            import math
            offset = (ball.pos.x - (self.paddle.x + self.paddle.width / 2)) / (self.paddle.width / 2)
            offset = max(-1.0, min(1.0, offset))
            speed = self.ball.vel.length()
            angle = offset * (math.pi / 3.0)  # up to 60 degrees from vertical
            ball.vel = Vec(speed * math.sin(angle), -speed * math.cos(angle))
            ball.pos.y = min(ball.pos.y, self.paddle.y - ball.radius)
            return "paddle"
        # brick hit
        brick = self.bricks[index]
        reflect_off_rect(ball, (brick.x, brick.y, brick.width, brick.height))
        brick.hits -= 1
        if not brick.alive:
            self.score += 10 * self.level_number
            if brick.power:
                self.power_ups.append(PowerUp(brick.x + brick.width / 2,
                                              brick.y + brick.height / 2, brick.power))
            if all(not b.alive for b in self.bricks):
                self.won = True
            else:
                drop = POWER_DROPS[(self.frame + index) % len(POWER_DROPS)]
                if drop != "none":
                    self.power_ups.append(PowerUp(brick.x + brick.width / 2,
                                                  brick.y + brick.height / 2, drop))
            return f"brick:{index}"
        return "brick-hit"

    # --- rendering -----------------------------------------------------------

    def render(self) -> str:
        width = int(FIELD_W / 2)
        height = int(FIELD_H / 2)
        grid = [[" "] * width for _ in range(height)]
        for brick in self.bricks:
            if not brick.alive:
                continue
            x0 = int(brick.x / 2)
            y0 = int(brick.y / 2)
            x1 = int((brick.x + brick.width) / 2 + 0.5)
            y1 = int((brick.y + brick.height) / 2 + 0.5)
            for y in range(max(y0, 0), min(y1, height)):
                for x in range(max(x0, 0), min(x1, width)):
                    grid[y][x] = "▤"
        for pu in self.power_ups:
            gx, gy = int(pu.x / 2), int(pu.y / 2)
            if 0 <= gy < height and 0 <= gx < width:
                grid[gy][gx] = "◆"
        px = int((self.paddle.x + self.paddle.width / 2) / 2)
        py = int(self.paddle.y / 2)
        if 0 <= px < width and 0 <= py < height:
            grid[py][px] = "▬"
        bx, by = int(self.ball.pos.x / 2), int(self.ball.pos.y / 2)
        if 0 <= bx < width and 0 <= by < height:
            grid[by][bx] = "●"
        lines = ["+" + "-" * width + "+"]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append("+" + "-" * width + "+")
        return "\n".join(lines)


POWER_DROPS = ("none", "none", "expand", "none", "slow")
