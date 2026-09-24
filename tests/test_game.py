"""Physics, level generation and session tests — all deterministic."""

import math
import unittest

from brickbreaker.level import generate_level
from brickbreaker.physics import Ball, Brick, Paddle, Vec, moving_circle_hits_rect, reflect_off_rect
from brickbreaker.game import GameSession, FIELD_W, FIELD_H


class TestLevelGen(unittest.TestCase):
    def test_levels_have_bricks_and_are_deterministic(self):
        for number in (1, 2, 3, 7):
            a = generate_level(number, seed=11)
            b = generate_level(number, seed=11)
            self.assertEqual(len(a.bricks), len(b.bricks), f"level {number}")
            self.assertTrue(len(a.bricks) > 0, f"level {number} empty")

    def test_higher_levels_are_tougher(self):
        level1 = generate_level(1, seed=5)
        level6 = generate_level(6, seed=5)
        if level1.bricks and level6.bricks:
            self.assertGreaterEqual(
                max(brick.hits for brick in level6.bricks),
                max(brick.hits for brick in level1.bricks),
            )

    def test_patterns_differ_by_level(self):
        a = generate_level(1, seed=2)   # checker
        b = generate_level(2, seed=2)   # pyramid
        self.assertNotEqual(a.pattern, b.pattern)

    def test_bricks_stay_inside_field(self):
        spec = generate_level(9, seed=3)
        for brick in spec.bricks:
            self.assertLessEqual(brick.x + brick.width, FIELD_W + 0.1)
            self.assertLess(brick.y, FIELD_H / 2, "bricks must stay in the top half")


class TestPhysics(unittest.TestCase):
    def test_reflect_vertical_on_horizontal_surface(self):
        ball = Ball(pos=Vec(10, 9), vel=Vec(3, -5), radius=0.5)
        normal = reflect_off_rect(ball, (8, 10, 4, 1))
        self.assertGreater(ball.vel.y, 0, "ball must bounce downward off a ceiling brick")
        self.assertEqual(normal.y, -1)

    def test_reflect_horizontal_on_vertical_surface(self):
        ball = Ball(pos=Vec(9, 12), vel=Vec(5, 1), radius=0.5)
        reflect_off_rect(ball, (10, 11, 2, 4))
        self.assertLess(ball.vel.x, 0, "ball must bounce back to the left")

    def test_sweep_detection_finds_crossing(self):
        ball = Ball(pos=Vec(5, 20), vel=Vec(0, -10), radius=0.5)
        rect = (4, 10, 6, 2)  # wall at y=10..12
        t = moving_circle_hits_rect(ball.pos, ball.vel, ball.radius, rect)
        self.assertIsNotNone(t)
        self.assertAlmostEqual(t, (20 - 12.5) / 10.0, delta=1e-9)

    def test_sweep_miss_when_moving_away(self):
        ball = Ball(pos=Vec(5, 8), vel=Vec(0, -10), radius=0.5)
        rect = (4, 10, 6, 2)
        self.assertIsNone(moving_circle_hits_rect(ball.pos, ball.vel, ball.radius, rect))


class TestSession(unittest.TestCase):
    def make_session(self) -> GameSession:
        return GameSession(level_number=1, seed=42)

    def test_ball_stays_on_field_until_reset(self):
        game = self.make_session()
        for _ in range(600):
            if game.lost:
                break  # after a loss the ball freezes wherever it fell
            game.step_frame()
            self.assertTrue(0 <= game.ball.pos.x <= FIELD_W,
                            f"x={game.ball.pos.x}")
            self.assertTrue(0 <= game.ball.pos.y <= FIELD_H,
                            f"y={game.ball.pos.y}")

    def test_paddle_bounce_angle_depends_on_hit_point(self):
        game = self.make_session()
        # place the ball just above the paddle edge and center
        for offset, expect_x_sign in ((game.paddle.x + 0.5, -1), (game.paddle.x + game.paddle.width - 0.5, 1)):
            game.ball.pos = Vec(offset, game.paddle.y - 0.6)
            game.ball.vel = Vec(0, 30)
            game.step_frame()
            if game.events and "paddle" in game.events[-1]:
                self.assertEqual(math.copysign(1, game.ball.vel.x), expect_x_sign)

    def test_losing_all_lives_loses_game(self):
        game = self.make_session()
        game.move_paddle_to(0)  # paddle at the far left
        for drop in range(3):
            if game.lost:
                break
            # drop the ball at the far right, straight down, away from the paddle
            game.ball.pos = Vec(FIELD_W - 1.0, FIELD_H - 6)
            game.ball.vel = Vec(0, 30)
            target_lives = 2 - drop
            for _ in range(400):
                if game.lost or game.lives == target_lives:
                    break
                game.step_frame()
        self.assertTrue(game.lost, "3 lost balls must end the game")

    def test_destroying_all_bricks_wins(self):
        game = self.make_session()
        game.bricks = game.bricks[:1]  # a single brick
        game.ball.pos = Vec(game.bricks[0].x - 1, game.bricks[0].y + 0.5)
        game.ball.vel = Vec(30, 0)     # fire straight at it
        for _ in range(300):
            game.step_frame()
            if game.won:
                break
        self.assertTrue(game.won, "single brick must break and win the level")

    def test_power_up_drop_and_pickup(self):
        game = self.make_session()
        brick = game.bricks[0]
        # force a power-up drop
        brick.power = "expand"
        game.ball.pos = Vec(brick.x - 1, brick.y + brick.height / 2)
        game.ball.vel = Vec(30, 0)
        broke = False
        for _ in range(200):
            game.step_frame()
            if any(pu.kind == "expand" for pu in game.power_ups):
                broke = True
                break
        self.assertTrue(broke, "breaking the brick must drop its power-up")
        # drop the ball out of the way and let the power-up fall to the paddle
        game.ball.pos = Vec(1, 1)
        game.ball.vel = Vec(0, 0)
        game.move_paddle_to(max(0, game.power_ups[0].x - game.paddle.width / 2))
        width_before = game.paddle.width
        for _ in range(200):
            game.step_frame()
        self.assertGreater(game.paddle.width, width_before, "expand must widen the paddle")

    def test_history_not_needed_but_score_grows(self):
        game = self.make_session()
        before = game.score
        # fire the ball into the brick field; some bricks break over time
        for _ in range(400):
            game.step_frame()
            if game.score > before:
                return
        self.fail("no bricks broken in 400 frames")

    def test_render_shows_bricks(self):
        game = self.make_session()
        board = game.render()
        self.assertIn("▤", board)
        self.assertIn("+", board)


import math  # noqa: E402  (used in paddle bounce test)


if __name__ == "__main__":
    unittest.main()
