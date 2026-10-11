"""The menus that open over the game: pause, settings and credits.

All three are overlays (see game/scene.py): the scene below waits, darkened, until
they close. Their words are in data/game.json under "ui".
"""
import pygame

from .. import assets, settings, ui
from ..scene import Overlay

BOX_W = 820
PLATE, EDGE = (30, 26, 28), (92, 78, 64)


class MenuOverlay(Overlay):
    """A heading and a column of choices in a box in the middle of the screen."""
    name = ""           # where its words are in "ui"
    pointer = True

    def __init__(self, game, choices):
        super().__init__(game)
        self.box = pygame.Rect(0, 0, BOX_W, 190 + len(choices) * ui.Menu.ROW)
        self.box.center = (settings.W // 2, settings.H // 2 - 20)
        self.menu = ui.Menu(choices, (self.box.centerx, self.box.top + 140))
        ui.panel(self.backdrop, self.box, PLATE, 250, radius=20, border=EDGE)
        ui.draw_text(self.backdrop, self.text(f"{self.name}.heading"), (self.box.centerx, self.box.top + 70), "title",
                     72, settings.WARM, center=True)

    def handle(self, dt, events):
        if ui.pressed(events, *ui.BACK, pygame.K_q):
            self.close()
        else:
            self.menu.update(dt, events)

    def paint(self, screen):
        self.menu.draw(screen)
        self.hint(screen, f"{self.name}.hint")


class Pause(MenuOverlay):
    name = "pause"
    hushed = True

    def __init__(self, game, below):
        self.below = below          # the scene that is waiting
        self.sure = False           # "back to the title" has been chosen once
        choices = [ui.Choice(game.content.text("pause.resume"), self.close),
                   ui.Choice(game.content.text("pause.settings"), self.settings)]
        if hasattr(below, "leave"):
            choices.append(ui.Choice(game.content.text("pause.leave"), lambda: self.close(then=below.leave)))
        choices.append(ui.Choice(self.title_label, self.title))
        super().__init__(game, choices)

    def settings(self):
        self.scenes.push(Settings(self.game))

    def title_label(self):
        return self.text("pause.sure" if self.sure else "pause.title")

    def title(self):
        """Giving up loses everything restored so far, so it has to be chosen twice."""
        if not self.sure:
            self.sure = True
            return
        from .title import Title
        self.scenes.go(lambda: Title(self.game))

    def handle(self, dt, events):
        if ui.pressed(events, pygame.K_p):
            self.close()
            return
        chosen = self.menu.cursor
        super().handle(dt, events)
        if self.menu.cursor != chosen:
            self.sure = False


class Settings(MenuOverlay):
    name = "settings"

    def __init__(self, game):
        text = game.content.text
        super().__init__(game, [
            ui.Choice(text("settings.music"), level=lambda: assets.levels["music"], change=self.set_music),
            ui.Choice(text("settings.sound"), level=lambda: assets.levels["sound"], change=self.set_sound),
            ui.Choice(self.fullscreen_label, game.display.toggle_fullscreen),
            ui.Choice(text("settings.back"), self.close),
        ])

    def set_music(self, level):
        assets.levels["music"] = level
        assets.muted = False            # whoever turns a volume up or down wants to hear it

    def set_sound(self, level):
        assets.levels["sound"] = level
        assets.muted = False

    def fullscreen_label(self):
        state = self.text("settings.on" if self.game.display.fullscreen else "settings.off")
        return f"{self.text('settings.fullscreen')}: {state}"


class Credits(Overlay):
    pointer = True
    WIDTH, GAP, BETWEEN = 1100, 8, 30       # the box, the space between lines and between blocks

    def __init__(self, game):
        super().__init__(game)
        credits = self.content.game["credits"]
        # (lines, text size, colour): the jam, the team, where the records come from
        blocks = [([credits["jam"]], 30, settings.WARM), (credits["team"], 30, settings.CREAM),
                  (credits["sources"], 24, settings.DIM)]
        inner = self.WIDTH - 120
        text_h = sum(len(ui.wrap(line, "pixel", size, inner)) * (assets.font("pixel", size).size("X")[1] + self.GAP)
                     for lines, size, _ in blocks for line in lines)
        self.box = pygame.Rect(0, 0, self.WIDTH, 170 + text_h + self.BETWEEN * (len(blocks) - 1))
        self.box.center = (settings.W // 2, settings.H // 2 - 20)
        ui.panel(self.backdrop, self.box, PLATE, 250, radius=20, border=EDGE)
        ui.draw_text(self.backdrop, self.text("credits.heading"), (self.box.centerx, self.box.top + 70), "title", 72,
                     settings.WARM, center=True)
        y = self.box.top + 136
        for lines, size, color in blocks:
            for line in lines:
                y = ui.draw_wrapped(self.backdrop, line, (self.box.x + 60, y), inner, "pixel", size, color,
                                    gap=self.GAP, center=True)
            y += self.BETWEEN

    def handle(self, dt, events):
        if ui.pressed(events, *ui.BACK, pygame.K_q) or ui.confirm(events) or ui.clicked(events):
            self.close()

    def paint(self, screen):
        self.hint(screen, "credits.hint")
