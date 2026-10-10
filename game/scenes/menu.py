"""The title screen."""
import math

import pygame

from .. import assets, settings, ui
from ..scene import Scene


class Menu(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.background = assets.backdrop("taustad/menu.png")
        self.ghost = assets.sprite("tegelased/down.png", scale=12)

    def update(self, dt, events):
        self.t += dt
        if ui.confirm(events) or ui.clicked(events):
            assets.play("enter.ogg", 0.4)
            self.game.new_game()
            from .intro import Intro
            self.scenes.go(lambda: Intro(self.game))

    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((30, 28, 34))
            pygame.draw.rect(screen, (44, 40, 44), (0, 760, settings.W, 320))
            bob = round(math.sin(self.t * 2) * 2) * 12
            screen.blit(self.ghost, self.ghost.get_rect(midbottom=(settings.W // 2, 810 + bob)))
        game = self.content.game
        ui.draw_text(screen, game["title"], (settings.W / 2, 250), "title", 190, settings.CREAM, center=True)
        ui.draw_text(screen, game["subtitle"], (settings.W / 2, 400), "italic", 50, settings.TEAL, center=True)
        ui.draw_text(screen, "press space to begin", (settings.W / 2, 930), "mono", 34, settings.WARM, center=True,
                     alpha=ui.blink(260))
        ui.hint(screen, "WASD / arrows move · E or space interact · M mute music · F fullscreen")
