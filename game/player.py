"""The ghost: four-direction walking with one sprite per direction.
Positions are in art pixels (see game/world.py)."""
import math

import pygame

from . import assets

SPEED = 62            # art pixels per second
FEET = (8, 4)         # the part of the sprite that collides
GLIDE = 22.0          # how quickly it picks up speed and comes to rest; a ghost does neither at once
SLIP = 4              # how far it drifts sideways by itself to get round a corner or into a doorway
DIRECTIONS = ("up", "down", "left", "right")


class Player:
    def __init__(self, pos, facing="down"):
        self.pos = pygame.Vector2(pos)      # bottom centre of the feet
        self.vel = pygame.Vector2()
        self.facing = facing
        self.moving = False
        self.hover = 0.0                    # where it is in its slow bob up and down
        self.images = {d: assets.sprite(f"tegelased/{d}.png", scale=1) for d in DIRECTIONS}      # in art pixels
        self.pictures = {d: assets.sprite(f"tegelased/{d}.png") for d in DIRECTIONS}             # at screen size

    @property
    def image(self):
        return self.images[self.facing]

    @property
    def picture(self):
        return self.pictures[self.facing]

    @property
    def lift(self):
        """How far the ghost is off its resting height just now, in art pixels."""
        return math.sin(self.hover)

    def feet(self, pos=None):
        pos = self.pos if pos is None else pos
        return pygame.Rect(round(pos.x) - FEET[0] // 2, round(pos.y) - FEET[1], *FEET)

    def update(self, dt, walkable, control=True):
        """walkable(rect) says whether the feet may stand there."""
        want = pygame.Vector2()
        if control:
            keys = pygame.key.get_pressed()
            want.x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            want.y = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        self.moving = want.length_squared() > 0
        self.hover += dt * (9 if self.moving else 2.4)
        if want.x:
            self.facing = "right" if want.x > 0 else "left"
        if want.y:
            self.facing = "down" if want.y > 0 else "up"
        if self.moving:
            want.scale_to_length(SPEED)
        self.vel += (want - self.vel) * (1 - math.exp(-GLIDE * dt))
        if not self.moving and self.vel.length_squared() < 1:
            self.vel.update(0, 0)
            return
        # one axis at a time, so the ghost slides along walls
        for axis in (0, 1):
            trial = pygame.Vector2(self.pos)
            trial[axis] += self.vel[axis] * dt
            if walkable(self.feet(trial)):
                self.pos = trial
                continue
            self.vel[axis] = 0
            if want[axis] and not want[1 - axis]:
                self._slip(axis, want[axis], dt, walkable)

    def _slip(self, axis, way, dt, walkable):
        """Walking straight at something that blocks: if the way is clear a few pixels to
        one side (the edge of a doorway, the corner of a table), drift over to it."""
        across = 1 - axis
        for off in range(1, SLIP + 1):
            for side in (-1, 1):
                beside = pygame.Vector2(self.pos)
                beside[across] += side * off
                ahead = pygame.Vector2(beside)
                ahead[axis] += math.copysign(1, way)
                if walkable(self.feet(beside)) and walkable(self.feet(ahead)):
                    step = pygame.Vector2(self.pos)
                    step[across] += side * min(off, SPEED * dt)
                    if walkable(self.feet(step)):
                        self.pos = step
                    return
