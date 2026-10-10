"""The Game object: owns the content, the player's progress and the scene manager."""
import pygame

from . import assets, settings, ui
from .content import Content
from .scene import SceneManager
from .state import GameState


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.canvas = pygame.Surface((settings.CANVAS_W, settings.CANVAS_H))
        self.running = True
        self.content = Content()
        self.state = GameState(self.content)
        self.scenes = SceneManager()
        from .scenes.menu import Menu
        self.scenes.start(Menu(self))

    def new_game(self):
        self.state = GameState(self.content)

    def update(self, dt, events):
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
        if ui.pressed(events, pygame.K_m):
            assets.toggle_mute()
        self.scenes.update(dt, events)

    def draw(self):
        self.scenes.draw(self.canvas, self.screen)
