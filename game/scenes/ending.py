"""The paperwork is done: closing words and credits."""
from .. import assets, settings, ui
from ..scene import Scene

PACE = 0.55           # seconds between one paragraph starting to appear and the next


class Ending(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.data = self.content.game["ending"]
        self.t = 0.0
        # keys are listened to once everything has appeared, so the ending is not skipped by accident
        self.wait = 1.0 + (len(self.data["text"]) + 1) * PACE

    def update(self, dt, events):
        self.t += dt
        if self.t > self.wait and (ui.confirm(events) or ui.clicked(events)):
            assets.play("tick.ogg", 0.6)
            from .title import Title
            self.scenes.go(lambda: Title(self.game))

    def shade(self, n):
        """How solid the n-th block of text is by now, 0..255: they appear one after another."""
        return max(0, min(255, int((self.t - 0.3 - n * PACE) / 0.7 * 255)))

    def draw(self, screen):
        screen.fill((22, 22, 28))
        x, width = 300, settings.W - 600
        ui.draw_text(screen, self.data["heading"], (settings.W / 2, 150), "title", 120, settings.CREAM, center=True,
                     alpha=self.shade(0))
        y = 280
        for n, para in enumerate(self.data["text"], 1):
            y = ui.draw_wrapped(screen, para, (x, y), width, "body", 40, settings.CREAM, center=True,
                                alpha=self.shade(n)) + 28
        y += 30
        after = len(self.data["text"]) + 1
        for line in self.data["credits"]:
            y = ui.draw_wrapped(screen, line, (x, y), width, "mono", 26, settings.DIM, center=True,
                                alpha=self.shade(after)) + 10
        if self.t > self.wait:
            self.hint(screen, "ending.back")
