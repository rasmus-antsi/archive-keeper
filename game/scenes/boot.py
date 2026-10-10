"""Loads everything once, behind a progress bar, so nothing stutters later."""
import os

from .. import assets, settings, ui
from ..scene import Scene


class Boot(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.steps = list(self.jobs())
        self.done = 0

    def jobs(self):
        """One small piece of loading per frame."""
        for role, size in (("title", 190), ("title", 96), ("title", 60), ("body", 44), ("body", 30), ("mono", 34),
                           ("mono", 26), ("mono", 24), ("italic", 50), ("bold", 36)):
            yield lambda role=role, size=size: assets.font(role, size)
        for folder in ("tegelased", "objektid", "props"):
            for name in sorted(os.listdir(f"assets/img/{folder}")) if os.path.isdir(f"assets/img/{folder}") else []:
                yield lambda name=f"{folder}/{name}": assets.optional(name)
        for name in sorted(os.listdir("assets/snd")):
            yield lambda name=name: assets.sound(name)
        yield lambda: self.game.world("archive", self.content.game["map"])
        for doc in self.content.documents:
            yield lambda doc=doc: self.game.world(doc["id"], doc["map"])

    def update(self, dt, events):
        if self.done < len(self.steps):
            self.steps[self.done]()
            self.done += 1
        else:
            from .menu import Menu
            self.scenes.go(lambda: Menu(self.game))

    def draw(self, screen):
        screen.fill((22, 20, 26))
        x, width = settings.W // 2 - 300, 600
        ui.draw_text(screen, "dusting the shelves", (settings.W / 2, settings.H / 2 - 50), "mono", 30, settings.DIM,
                     center=True)
        screen.fill((48, 44, 52), (x, settings.H // 2, width, 8))
        screen.fill(settings.TEAL, (x, settings.H // 2, width * self.done // max(1, len(self.steps)), 8))
