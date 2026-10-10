"""The paperwork is done: closing words and credits."""
from .. import settings, ui
from ..scene import Scene


class Ending(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.data = self.content.game["ending"]
        self.t = 0.0

    def update(self, dt, events):
        self.t += dt
        if self.t > 1.5 and (ui.confirm(events) or ui.clicked(events)):
            from .menu import Menu
            self.scenes.go(lambda: Menu(self.game))

    def draw(self, screen):
        screen.fill((22, 22, 28))
        x, width = 300, settings.W - 600
        ui.draw_text(screen, self.data["heading"], (settings.W / 2, 150), "title", 120, settings.CREAM, center=True)
        y = 280
        for para in self.data["text"]:
            y = ui.draw_wrapped(screen, para, (x, y), width, "body", 40, settings.CREAM, center=True) + 28
        y += 30
        for line in self.data["credits"]:
            y = ui.draw_wrapped(screen, line, (x, y), width, "mono", 26, settings.DIM, center=True) + 10
        if self.t > 1.5:
            ui.hint(screen, "space — back to the title")
