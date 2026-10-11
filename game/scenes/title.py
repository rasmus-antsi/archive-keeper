"""The title screen: the game's name and the first menu."""
import math

import pygame

from .. import assets, settings, ui
from ..display import WEB
from ..scene import Scene


class Title(Scene):
    music = "menu"
    pointer = True

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.art = assets.backdrop("taustad/menu.png")
        self.page = self.compose()
        self.ghost = assets.sprite("tegelased/down.png")
        choices = [ui.Choice(self.text("title.begin"), self.begin),
                   ui.Choice(self.text("title.settings"), self.settings),
                   ui.Choice(self.text("title.credits"), self.credits)]
        if not WEB:             # in the browser, leaving is closing the tab
            choices.append(ui.Choice(self.text("title.quit"), self.quit))
        self.menu = ui.Menu(choices, (settings.W // 2, 0))
        self.menu.y = 830 - self.menu.height // 2

    def compose(self):
        """Everything that never moves, as one picture: letters this big are costly to draw
        again every frame."""
        page = pygame.Surface((settings.W, settings.H)).convert()
        if self.art:
            page.blit(self.art, (0, 0))
        else:                   # until there is a painting: a dark room for the ghost to stand in
            page.fill((30, 28, 34))
            page.fill((44, 40, 44), (0, 640, settings.W, settings.H - 640))
        game = self.content.game
        ui.draw_text(page, game["title"], (settings.W / 2, 250), "title", 190, settings.CREAM, center=True)
        ui.draw_text(page, game["subtitle"], (settings.W / 2, 400), "pixel", 50, settings.TEAL, center=True)
        return page

    def begin(self):
        assets.play("enter.ogg", 0.4)
        self.game.new_game()
        from .intro import Intro
        self.scenes.go(lambda: Intro(self.game))

    def settings(self):
        from .pause import Settings
        self.scenes.push(Settings(self.game))

    def credits(self):
        from .pause import Credits
        self.scenes.push(Credits(self.game))

    def quit(self):
        self.game.running = False

    def update(self, dt, events):
        self.t += dt
        self.menu.update(dt, events)

    def draw(self, screen):
        screen.blit(self.page, (0, 0))
        if not self.art:
            bob = round(math.sin(self.t * 2) * 8)
            screen.blit(self.ghost, self.ghost.get_rect(midbottom=(settings.W // 2, 668 + bob)))
        self.menu.draw(screen)
        self.hint(screen, "title.hint")
