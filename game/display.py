"""The window. Scenes always draw on a 1920x1080 surface; this fits it into
whatever window there is, converts mouse positions back and keeps time.

In the browser the surface is the canvas itself: the web page scales it and the
browser asks for one frame per screen refresh, so nothing is copied and nothing
waits. On the desktop the window is resizable, F toggles fullscreen, and frames
follow the screen's refresh (vsync) where the system allows it.
"""
import collections
import os
import sys
import time
import warnings

import pygame

from . import settings

WEB = sys.platform == "emscripten"
MAX_STEP = 0.05         # the longest the game is ever moved on in one frame, in seconds
ICON = "favicon.png"


class Display:
    def __init__(self):
        self.size = (settings.W, settings.H)
        self.clock = pygame.time.Clock()
        self.cap = 0                                     # frames a second to hold the loop to; 0: nothing waits
        self.vsync = False
        self.recent = collections.deque(maxlen=8)        # the last few frame times, in seconds
        self.last = time.perf_counter()
        if WEB:
            # no SCALED or RESIZABLE here: the page stretches the canvas, and a second
            # scaler inside SDL is what makes mouse positions drift
            self.window = pygame.display.set_mode(self.size)
            self.surface = self.window
        else:
            self.window = self._open_window()
            self.surface = pygame.Surface(self.size).convert()
        pygame.display.set_caption(settings.TITLE)
        self.view = pygame.Rect((0, 0), self.size)       # where the picture sits in the window
        self.fitted = None                               # the window size the view was worked out for

    def _open_window(self):
        if os.path.isfile(ICON):
            pygame.display.set_icon(pygame.image.load(ICON))
        desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
        k = min(1.0, (desk_w - 80) / settings.W, (desk_h - 140) / settings.H)
        size = (int(settings.W * k), int(settings.H * k))
        with warnings.catch_warnings(record=True) as complaints:
            warnings.simplefilter("always")
            try:
                # with vsync, flip() waits for the screen, so every frame is shown for the same time
                window = pygame.display.set_mode(size, pygame.RESIZABLE, vsync=1)
                self.vsync = not complaints       # pygame warns when the system could not give it
            except pygame.error:
                window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self._follow_screen()
        return window

    def _follow_screen(self):
        """Set the frame cap for the screen the window is on. With vsync the cap sits above
        the refresh rate, so it never waits; it only stops a runaway loop on a system that
        accepts vsync and then ignores it."""
        try:
            refresh = pygame.display.get_current_refresh_rate()
        except pygame.error:
            refresh = 0
        self.cap = int((refresh or settings.FPS) * 1.25) + 1 if self.vsync else settings.FPS

    # ---------------------------------------------------------------- time

    def tick(self):
        """Wait for the next frame if anything has to, and return the seconds to move the game on by.

        A measured frame time wobbles by a millisecond even when frames arrive evenly, and
        uneven steps are what makes scrolling look jerky, so the step is the average of the
        last few. A frame that took far too long (loading, a hidden browser tab) is cut short.
        """
        self.clock.tick(self.cap)
        now = time.perf_counter()
        self.recent.append(min(now - self.last, MAX_STEP))
        self.last = now
        return sum(self.recent) / len(self.recent)

    @property
    def fps(self):
        return self.clock.get_fps()

    # ---------------------------------------------------------------- fullscreen

    @property
    def fullscreen(self):
        if WEB:
            return bool(_page("is_fullscreen"))
        return pygame.display.is_fullscreen()

    def toggle_fullscreen(self):
        if WEB:
            _page("toggle_fullscreen")
        else:
            pygame.display.toggle_fullscreen()

    # ---------------------------------------------------------------- mouse

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
            elif e.type == pygame.WINDOWDISPLAYCHANGED:
                self._follow_screen()         # dragged to a screen with another refresh rate
            out.append(e)
        return out

    # ---------------------------------------------------------------- drawing

    def present(self):
        if self.surface is not self.window:
            if self.window.get_size() != self.fitted:
                self._fit()
            if self.view.size == self.size:
                self.window.blit(self.surface, self.view)
            else:
                pygame.transform.smoothscale(self.surface, self.view.size, self.window.subsurface(self.view))
        pygame.display.flip()

    def _fit(self):
        """Centre the picture in the window, as large as it goes without changing its shape."""
        self.fitted = win_w, win_h = self.window.get_size()
        k = min(win_w / settings.W, win_h / settings.H)
        self.view = pygame.Rect(0, 0, max(1, int(settings.W * k)), max(1, int(settings.H * k)))
        self.view.center = (win_w // 2, win_h // 2)
        self.window.fill((0, 0, 0))           # the bars beside the picture


def _page(name):
    """Call one of the helper functions web/pygbag.tmpl puts on the web page."""
    try:
        import platform
        return getattr(platform.window, name)()
    except Exception:           # another page template, or a browser that refuses
        return None
