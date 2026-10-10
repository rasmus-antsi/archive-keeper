"""The ghost: four-direction walking with one sprite per direction.
Positions are in art pixels (see game/world.py)."""
import math

import pygame

from . import assets

SPEED = 62            # art pixels per second
FEET = (8, 4)         # the part of the sprite that collides


class Player:
    def __init__(self, pos, facing="down"):
        self.pos = pygame.Vector2(pos)      # bottom centre of the feet
        self.facing = facing
        self.moving = False
        self.t = 0.0
        self.sprites = {d: assets.optional(f"tegelased/{d}.png") for d in ("up", "down", "left", "right")}

    def feet(self, pos=None):
        pos = self.pos if pos is None else pos
        return pygame.Rect(round(pos.x) - FEET[0] // 2, round(pos.y) - FEET[1], *FEET)

    def update(self, dt, walkable, control=True):
        """walkable(rect) says whether the feet may stand there."""
        self.t += dt
        move = pygame.Vector2()
        if control:
            keys = pygame.key.get_pressed()
            move.x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            move.y = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        self.moving = move.length_squared() > 0
        if not self.moving:
            return
        if move.x:
            self.facing = "right" if move.x > 0 else "left"
        if move.y:
            self.facing = "down" if move.y > 0 else "up"
        step = move.normalize() * SPEED * dt
        # one axis at a time, so the ghost slides along walls
        for axis in (0, 1):
            trial = pygame.Vector2(self.pos)
            trial[axis] += step[axis]
            if walkable(self.feet(trial)):
                self.pos = trial

    def actor(self):
        """(y of the feet, picture, top left) for World.draw. The ghost hovers a little."""
        img = self.sprites[self.facing]
        bob = round(math.sin(self.t * (9 if self.moving else 2.4)))
        return self.pos.y, img, (round(self.pos.x) - img.get_width() // 2, round(self.pos.y) - img.get_height() - 1 + bob)
