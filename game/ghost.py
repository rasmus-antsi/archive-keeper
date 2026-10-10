"""The keeper: floaty, slow to start and slow to stop."""
import math

import pygame

from . import core

SPEED = 330          # world pixels per second
ACCEL = 3.6          # lower is floatier
SCALE = 0.42


class Ghost:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.t = 0.0
        self.facing = 1
        self.trail = []
        self.trail_timer = 0.0
        self.sprite = core.image("ghost.png", SCALE)
        self.shadow = pygame.Surface((70, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(self.shadow, (30, 14, 10, 70), self.shadow.get_rect())
        self._rotated = {}

    def update(self, dt, control=True, mouse_world=None, walkable=None):
        self.t += dt
        move = pygame.Vector2()
        if control:
            keys = pygame.key.get_pressed()
            move.x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            move.y = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            if move.length_squared() > 0:
                move = move.normalize()
            elif mouse_world is not None and pygame.mouse.get_pressed()[0]:
                # hold the mouse (or a finger) and the ghost drifts toward it
                to = mouse_world - self.pos
                if to.length() > 10:
                    move = to.normalize() * min(1.0, to.length() / 140)
        self.vel += (move * SPEED - self.vel) * min(1.0, ACCEL * dt)

        # walls stop the ghost one axis at a time, so it slides along them
        step = self.vel * dt
        for axis in (0, 1):
            trial = pygame.Vector2(self.pos)
            trial[axis] += step[axis]
            if walkable is None or walkable(trial):
                self.pos = trial
            else:
                self.vel[axis] = 0
        if abs(self.vel.x) > 20:
            self.facing = 1 if self.vel.x > 0 else -1

        self.trail_timer -= dt
        if self.trail_timer <= 0 and self.vel.length() > 30:
            self.trail_timer = 0.06
            self.trail.append([pygame.Vector2(self.pos), 1.0])
        for item in self.trail:
            item[1] -= dt * 1.5
        self.trail = [item for item in self.trail if item[1] > 0]

    def draw(self, surf, cam=(0, 0)):
        x, y = self.pos.x - cam[0], self.pos.y - cam[1]
        bob = math.sin(self.t * 2.1) * 4
        surf.blit(self.shadow, self.shadow.get_rect(center=(x, y + 34)))
        for pos, life in self.trail:
            core.add_glow(surf, (pos.x - cam[0], pos.y - cam[1] - 6), 20 * life + 8, core.TEAL, life * 0.3)
        core.add_glow(surf, (x, y - 24 + bob), 76, (90, 120, 110), 0.6 + 0.1 * math.sin(self.t * 1.3))

        angle = int(max(-14, min(14, -self.vel.x * 0.05)) / 2) * 2
        key = (angle, self.facing)
        if key not in self._rotated:
            img = self.sprite if self.facing > 0 else pygame.transform.flip(self.sprite, True, False)
            self._rotated[key] = pygame.transform.rotozoom(img, angle, 1.0)
        img = self._rotated[key]
        surf.blit(img, img.get_rect(center=(x, y - 30 + bob)))
