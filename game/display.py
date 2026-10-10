"""The window. Scenes always draw on a 1920x1080 surface; this fits it into
whatever window there is and converts mouse positions back.

In the browser the surface is the canvas itself and the web page scales it, so
nothing is copied. On the desktop the window is resizable and F toggles fullscreen.
"""
import sys

import pygame

from . import settings

WEB = sys.platform == "emscripten"


class Display:
    def __init__(self):
        self.size = (settings.W, settings.H)
        if WEB:
            # no SCALED or RESIZABLE here: the page stretches the canvas, and a second
            # scaler inside SDL is what makes mouse positions drift
            self.window = pygame.display.set_mode(self.size)
            self.surface = self.window
        else:
            desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
            k = min(1.0, (desk_w - 80) / settings.W, (desk_h - 140) / settings.H)
            self.window = pygame.display.set_mode((int(settings.W * k), int(settings.H * k)), pygame.RESIZABLE)
            self.surface = pygame.Surface(self.size).convert()
        pygame.display.set_caption(settings.TITLE)
        self.view = pygame.Rect((0, 0), self.size)       # where the picture sits in the window

    def toggle_fullscreen(self):
        if not WEB:
            pygame.display.toggle_fullscreen()

    def to_game(self, pos):
        """A window position as a position on the 1920x1080 surface."""
        if self.surface is self.window:
            return pos
        return ((pos[0] - self.view.x) * settings.W / self.view.w, (pos[1] - self.view.y) * settings.H / self.view.h)

    def mouse(self):
        return self.to_game(pygame.mouse.get_pos())

    def translate(self, events):
        """Rewrite mouse events so their positions are in game coordinates."""
        if self.surface is self.window:
            return events
        out = []
        for e in events:
            if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                e = pygame.event.Event(e.type, {**e.dict, "pos": self.to_game(e.pos)})
            out.append(e)
        return out

    def present(self):
        if self.surface is not self.window:
            win_w, win_h = self.window.get_size()
            k = min(win_w / settings.W, win_h / settings.H)
            self.view = pygame.Rect(0, 0, max(1, int(settings.W * k)), max(1, int(settings.H * k)))
            self.view.center = (win_w // 2, win_h // 2)
            if self.view.size == self.size:
                self.window.blit(self.surface, self.view)
            else:
                self.window.fill((0, 0, 0))
                pygame.transform.smoothscale(self.surface, self.view.size, self.window.subsurface(self.view))
        pygame.display.flip()
