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
        self.ghost = pygame.transform.scale_by(assets.sprite("tegelased/down.png", (14, 25)), 2)

    def update(self, dt, events):
        self.t += dt
        if ui.confirm(events) or ui.clicked(events):
            assets.play("enter.ogg", 0.4)
            self.game.new_game()
            from .intro import Intro
            self.scenes.go(lambda: Intro(self.game))

    def draw(self, canvas):
        canvas.fill((30, 28, 34))
        pygame.draw.rect(canvas, (44, 40, 44), (0, 168, settings.CANVAS_W, 72))
        bob = round(math.sin(self.t * 2) * 2)
        canvas.blit(self.ghost, self.ghost.get_rect(midbottom=(settings.CANVAS_W // 2, 178 + bob)))

    def draw_ui(self, screen):
        game = self.content.game
        ui.draw_text(screen, game["title"], (settings.W / 2, 190), "title", 110, settings.CREAM, center=True)
        ui.draw_text(screen, game["subtitle"], (settings.W / 2, 280), "italic", 30, settings.TEAL, center=True)
        ui.draw_text(screen, "press space to begin", (settings.W / 2, 610), "mono", 20, settings.WARM, center=True,
                     alpha=ui.blink(260))
        ui.hint(screen, "WASD / arrows move · E or space interact · M mute music")
