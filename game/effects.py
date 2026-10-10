"""Screen transitions drawn over a scene. k runs from 0 (nothing) to 1 (fully covered).

Darkening and whitening lay a sheet of one colour, see-through as a whole, over the
picture. That is the cheap way in the browser: measured there, it takes 1.4 ms for the
full screen, against 8 ms for pygame's multiply and add fills (which win on the desktop).
"""
import math

import pygame

from . import settings

_small = _big = None
_sheets = {}
KEY = (255, 0, 255)


def ease(k):
    """A soft start and a soft stop for anything that runs from 0 to 1."""
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def cover(screen, color, k):
    """Mix the whole picture towards one colour: 0 leaves it alone, 1 hides it."""
    alpha = round(255 * max(0.0, min(1.0, k)))
    if not alpha:
        return
    sheet = _sheets.get(color)
    if sheet is None:
        sheet = _sheets[color] = pygame.Surface((settings.W, settings.H)).convert()
        sheet.fill(color)
    sheet.set_alpha(alpha)
    screen.blit(sheet, (0, 0))


def darken(screen, k):
    cover(screen, (0, 0, 0), k)


def whiten(screen, k):
    cover(screen, (255, 255, 255), k)


def fade(screen, k, t, closing):
    darken(screen, ease(k))


def spiral(screen, k, t, closing):
    """Falling through time: dark spiral arms wind outwards and a white light swallows
    the screen. The new scene then appears out of the white. Drawn small and enlarged,
    like the rooms, so it costs almost nothing."""
    global _small, _big
    if not closing:
        whiten(screen, ease(k))
        return
    if _small is None:
        _small = pygame.Surface((settings.VIEW_W, settings.VIEW_H)).convert()
        _big = pygame.Surface((settings.W, settings.H)).convert()
        _big.set_colorkey(KEY)
    darken(screen, 0.75 * k)
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
