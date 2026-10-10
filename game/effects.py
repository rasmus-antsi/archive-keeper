"""Screen transitions drawn over a scene. k runs from 0 (nothing) to 1 (fully covered)."""
import math

import pygame

from . import settings

_veil = _small = _big = None
KEY = (255, 0, 255)


def _cover(screen, color, alpha):
    global _veil
    if _veil is None:
        _veil = pygame.Surface((settings.W, settings.H))
    _veil.fill(color)
    _veil.set_alpha(max(0, min(255, int(alpha))))
    screen.blit(_veil, (0, 0))


def fade(screen, k, t, closing):
    _cover(screen, (0, 0, 0), 255 * k)


def spiral(screen, k, t, closing):
    """Falling through time: dark spiral arms wind outwards and a white light swallows
    the screen. The new scene then appears out of the white. Drawn small and enlarged,
    like the rooms, so it costs almost nothing."""
    global _small, _big
    if not closing:
        _cover(screen, (255, 255, 255), 255 * k)
        return
    if _small is None:
        _small = pygame.Surface((settings.VIEW_W, settings.VIEW_H)).convert()
        _big = pygame.Surface((settings.W, settings.H)).convert()
        _big.set_colorkey(KEY)
    _cover(screen, (0, 0, 0), 190 * k)
    _small.fill(KEY)
    cx, cy = settings.VIEW_W // 2, settings.VIEW_H // 2
    pitch = 5.8                             # how fast an arm moves outwards, pixels per radian
    reach = 160 * min(1.0, k * 1.5)         # the arms grow from the centre to past the corners
    for arm, color in enumerate(((0, 0, 0), (150, 150, 150))):
        angle = 0.6
        while angle * pitch < reach:
            radius = angle * pitch
            turn = angle - t * 5 + arm * math.pi
            pygame.draw.circle(_small, color, (cx + math.cos(turn) * radius * 1.2, cy + math.sin(turn) * radius),
                               1.5 + radius * 0.055)
            angle += 0.06
    pygame.draw.circle(_small, (255, 255, 255), (cx, cy), 4 * k + 160 * k ** 6)
    pygame.transform.scale(_small, (settings.W, settings.H), _big)
    screen.blit(_big, (0, 0))


EFFECTS = {"fade": (fade, 0.35, 0.45), "spiral": (spiral, 1.3, 0.8)}      # draw, seconds out, seconds in
