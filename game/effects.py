"""Screen transitions drawn over a scene. k runs from 0 (nothing) to 1 (fully covered)."""
import math

import pygame

from . import settings

_veil = None
CENTRE = (settings.W // 2, settings.H // 2)


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
    the screen. The new scene then appears out of the white."""
    if not closing:
        _cover(screen, (255, 255, 255), 255 * k)
        return
    _cover(screen, (0, 0, 0), 190 * k)
    pitch = 46                              # how fast an arm moves outwards, pixels per radian
    reach = 1250 * min(1.0, k * 1.5)        # the arms grow from the centre to past the corners
    for arm, color in enumerate(((0, 0, 0), (150, 150, 150))):
        angle = 0.6
        while angle * pitch < reach:
            radius = angle * pitch
            turn = angle - t * 5 + arm * math.pi
            pos = (CENTRE[0] + math.cos(turn) * radius * 1.2, CENTRE[1] + math.sin(turn) * radius)
            pygame.draw.circle(screen, color, pos, 12 + radius * 0.055)
            angle += 0.045
    pygame.draw.circle(screen, (255, 255, 255), CENTRE, 30 * k + 1250 * k ** 6)


EFFECTS = {"fade": (fade, 0.35, 0.45), "spiral": (spiral, 1.3, 0.8)}      # draw, seconds out, seconds in
