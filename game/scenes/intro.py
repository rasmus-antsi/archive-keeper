"""The robots' opening message, a paragraph at a time: each one is typed out and
then waits for a key. Esc skips the rest."""
from .. import assets, settings, ui
from ..scene import Scene

TYPE_SPEED = 70       # characters per second


class Intro(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        data = self.content.game["intro"]
        self.heading = data["heading"]
        self.paragraphs = data["text"]
        self.page = 0             # which paragraph is on the screen
        self.t = 0.0              # seconds it has been typing

    @property
    def last(self):
        return self.page == len(self.paragraphs) - 1

    def typed(self):
        return self.t * TYPE_SPEED >= len(self.paragraphs[self.page])

    def begin(self):
        from .archive import Archive
        self.scenes.go(lambda: Archive(self.game))

    def update(self, dt, events):
        self.t += dt
        if ui.pressed(events, *ui.BACK):
            self.begin()
        elif ui.confirm(events) or ui.clicked(events):
            if not self.typed():
                self.t = len(self.paragraphs[self.page]) / TYPE_SPEED       # first press shows the whole paragraph
                return
            assets.play("tick.ogg", 0.6)
            if self.last:
                self.begin()
            else:
                self.page, self.t = self.page + 1, 0.0

    def draw(self, screen):
        screen.fill((10, 14, 16))
        x, width = 300, settings.W - 600
        ui.draw_text(screen, self.heading, (x, 230), "pixel", 28, settings.TEAL)
        count = ui.text(f"{self.page + 1} / {len(self.paragraphs)}", "pixel", 28, settings.DIM)
        screen.blit(count, (x + width - count.get_width(), 230))
        screen.fill((40, 60, 62), (x, 280, width, 4))
        lines = ui.wrap(self.paragraphs[self.page], "pixel", 40, width)
        ui.draw_typed(screen, lines, self.t * TYPE_SPEED, (x, 330), "pixel", 40, step=56)
        self.hint(screen, "intro.typing" if not self.typed() else "intro.begin" if self.last else "intro.next")
