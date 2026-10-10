"""The Game object: owns the content, the player's progress and the scene manager."""
import pygame

from . import assets, settings, ui
from .content import Content
from .scene import SceneManager
from .state import GameState


class Game:
    def __init__(self, display):
        self.display = display
        self.screen = display.surface
        self.running = True
        self.fps = 0.0
        self.show_fps = False
        self.content = Content()
        self.state = GameState(self.content)
        self.scenes = SceneManager()
        from .scenes.menu import Menu
        self.scenes.start(Menu(self))

    def new_game(self):
        self.state = GameState(self.content)

    def update(self, dt, events, fps=0.0):
        self.fps = fps
        events = self.display.translate(events)
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
        if ui.pressed(events, pygame.K_m):
            assets.toggle_mute()
        if ui.pressed(events, pygame.K_f, pygame.K_F11):
            self.display.toggle_fullscreen()
        if ui.pressed(events, pygame.K_F3):
            self.show_fps = not self.show_fps
        self.scenes.update(dt, events)

    def draw(self):
        self.scenes.draw(self.screen)
        if self.show_fps:       # F3: frame rate, and a cross where the game thinks the mouse is
            x, y = (round(v) for v in self.display.mouse())
            pygame.draw.line(self.screen, settings.RED, (x - 30, y), (x + 30, y), 3)
            pygame.draw.line(self.screen, settings.RED, (x, y - 30), (x, y + 30), 3)
            ui.panel(self.screen, (settings.W - 420, 8, 412, 44))
            ui.draw_text(self.screen, f"{self.fps:3.0f} fps  mouse {x},{y}", (settings.W - 408, 16), "mono", 24, settings.WARM)
