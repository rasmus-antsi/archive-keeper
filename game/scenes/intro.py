"""The robots' opening message: typed out, held for a while, skippable."""
from .. import settings, ui
from ..scene import Scene

TYPE_SPEED = 70       # characters per second


class Intro(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        data = self.content.game["intro"]
        self.heading = data["heading"]
        self.paragraphs = data["text"]
        self.length = sum(len(p) for p in self.paragraphs)
        self.seconds = max(data.get("seconds", 20), self.length / TYPE_SPEED + 4)
        self.t = 0.0

    def typed(self):
        return self.t * TYPE_SPEED >= self.length

    def update(self, dt, events):
        self.t += dt
        skip = ui.confirm(events) or ui.clicked(events)
        if skip and not self.typed():
            self.t = self.length / TYPE_SPEED       # first press shows the whole text
        elif skip or self.t >= self.seconds:
            from .archive import Archive
            self.scenes.go(lambda: Archive(self.game))

    def draw(self, screen):
        screen.fill((10, 14, 16))
        x, width = 300, settings.W - 600
        ui.draw_text(screen, self.heading, (x, 110), "mono", 28, settings.TEAL)
        left = int(self.t * TYPE_SPEED)
        y = 190
        for para in self.paragraphs:
            if left <= 0:
                break
            y = ui.draw_wrapped(screen, para[:left], (x, y), width, "mono", 34, settings.CREAM, gap=10) + 26
            left -= len(para)
        # time left before the game starts on its own
        k = max(0.0, 1 - self.t / self.seconds)
        screen.fill((40, 60, 62), (x, settings.H - 90, width, 4))
        screen.fill(settings.TEAL, (x, settings.H - 90, int(width * k), 4))
        ui.hint(screen, "space — continue" if self.typed() else "space — skip")
