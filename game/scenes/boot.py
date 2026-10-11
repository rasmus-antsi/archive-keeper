"""Loads everything once, behind a progress bar, so nothing stutters later."""
import math
import os
import time

from .. import assets, settings, ui
from ..scene import Scene
from . import memory

SLICE = 0.008         # seconds of loading done per frame; the rest keeps the screen alive

# every (role, size) the game writes with; tools/smoke.py fails when one is missing here
FONTS = (("mono", 30), ("mono", 40), ("title", 190), ("title", 120), ("title", 96), ("title", 72), ("title", 60), ("title", 48),
         ("body", 44), ("body", 40), ("body", 36), ("body", 30), ("bold", 48), ("bold", 36), ("italic", 50),
         ("italic", 44), ("italic", 30), ("italic", 28), ("mono", 34), ("mono", 28), ("mono", 26), ("mono", 24),
         ("mono", 22), ("mono", 20), ("mono", 18))


class Boot(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.steps = list(self.jobs())
        self.done = 0
        self.bar = 0.0            # what the bar shows; it runs smoothly after the real progress
        self.t = 0.0

    def jobs(self):
        """Everything there is to load, in small pieces."""
        yield lambda: assets.sprite("tegelased/down.png")
        for role, size in FONTS:
            yield lambda role=role, size=size: assets.font(role, size)
        for folder in ("tegelased", "objektid", "props"):
            for name in sorted(os.listdir(f"assets/img/{folder}")) if os.path.isdir(f"assets/img/{folder}") else []:
                yield lambda name=f"{folder}/{name}": assets.optional(name)
        for name in sorted(os.listdir("assets/snd")):
            yield lambda name=name: assets.sound(name)
        yield lambda: self.game.world("archive", self.content.game["map"])
        for doc in self.content.documents:
            yield lambda doc=doc: self.game.world(doc["id"], doc["map"])
            yield lambda doc=doc: memory.warm_up(doc)

    def update(self, dt, events):
        self.t += dt
        started = time.perf_counter()
        while self.done < len(self.steps) and time.perf_counter() - started < SLICE:
            self.steps[self.done]()
            self.done += 1
        self.bar += (self.done / len(self.steps) - self.bar) * (1 - math.exp(-24 * dt))
        if self.done == len(self.steps) and self.bar > 0.99:
            from .title import Title
            self.scenes.go(lambda: Title(self.game))

    def draw(self, screen):
        screen.fill((22, 20, 26))
        x, y, width = settings.W // 2 - 300, settings.H // 2 + 40, 600
        if self.done:             # the first job loads the ghost
            ghost = assets.sprite("tegelased/down.png")
            screen.blit(ghost, ghost.get_rect(midbottom=(settings.W // 2, y - 110 + round(math.sin(self.t * 3) * 6))))
        if self.done > 1:         # and the second the font
            ui.draw_text(screen, self.text("loading"), (settings.W / 2, y - 50), "mono", 30, settings.DIM, center=True)
        screen.fill((48, 44, 52), (x, y, width, 8))
        screen.fill(settings.TEAL, (x, y, round(width * self.bar), 8))
