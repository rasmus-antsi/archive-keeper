"""The Game object: owns the content, the player's progress and the scene manager."""
import pygame

from . import assets, settings, ui
from .content import Content
from .display import WEB
from .scene import SceneManager
from .state import GameState


class Game:
    def __init__(self, display):
        self.display = display
        self.screen = display.surface
        self.running = True
        self.show_fps = False
        self.content = Content()
        assets.track_levels.update(self.content.game.get("music", {}))
        self.state = GameState(self.content)
        self.scenes = SceneManager()
        self.worlds = {}
        from .scenes.boot import Boot
        self.scenes.start(Boot(self))

    def world(self, name, data):
        """The place with this name, built once and kept: painting one takes a moment."""
        if name not in self.worlds:
            from .world import World
            self.worlds[name] = World(name, data)
        return self.worlds[name]

    def new_game(self):
        self.state = GameState(self.content)

    def update(self, dt, events):
        events = self.display.translate(events)
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
        if ui.pressed(events, pygame.K_m):
            ui.toast(self.content.text("sound_off" if assets.toggle_mute() else "sound_on"))
        if ui.pressed(events, pygame.K_f, pygame.K_F11) and not WEB:     # in the browser the page listens for F itself
            self.display.toggle_fullscreen()
        if ui.pressed(events, pygame.K_F3):
            self.show_fps = not self.show_fps
        if ui.pressed(events, pygame.K_ESCAPE, pygame.K_p) and self.scenes.top.pausable and not self.scenes.busy:
            from .scenes.pause import Pause
            assets.play("tick.ogg", 0.6)
            self.scenes.push(Pause(self, self.scenes.top))
            events = []                 # the key that paused the game is not for the menu as well
        assets.update(dt)
        self.scenes.update(dt, events)

    def draw(self):
        self.scenes.draw(self.screen)
        ui.draw_toast(self.screen)
        if self.show_fps:       # F3: frame rate, and a cross where the game thinks the mouse is
            x, y = (round(v) for v in self.display.mouse())
            pygame.draw.line(self.screen, settings.RED, (x - 30, y), (x + 30, y), 3)
            pygame.draw.line(self.screen, settings.RED, (x, y - 30), (x, y + 30), 3)
            ui.panel(self.screen, (settings.W - 420, 8, 412, 44))
            ui.draw_text(self.screen, f"{self.display.fps:3.0f} fps  mouse {x},{y}", (settings.W - 408, 16), "pixel", 24, settings.WARM)
