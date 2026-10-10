"""The Scene base class and the SceneManager that runs a stack of them.

Scenes never touch each other; they ask the manager to go(), push() or pop().
"""
import pygame

from . import assets, settings


class Scene:
    music = None          # name of a track in assets/music, or None to leave it alone

    def __init__(self, game):
        self.game = game
        self.state = game.state
        self.content = game.content
        self.scenes = game.scenes

    def enter(self):
        """Called when the scene becomes the top of the stack, also on return from an overlay."""

    def update(self, dt, events):
        pass

    def draw(self, screen):
        pass


class SceneManager:
    FADE_OUT, FADE_IN = 0.35, 0.45

    def __init__(self):
        self.stack = []
        self.pending = None       # a factory that builds the next scene once the screen is black
        self.fade = 1.0
        self.black = pygame.Surface((settings.W, settings.H))

    @property
    def top(self):
        return self.stack[-1]

    def start(self, scene):
        self.stack = [scene]
        self._entered()

    def go(self, factory):
        """Fade to black, replace the whole stack with factory(), fade back in."""
        if self.pending is None:
            self.pending = factory

    def push(self, scene):
        """Open an overlay on top of the current scene, without a fade. Only the top scene
        is drawn; an overlay that wants the old picture behind it keeps a copy of the screen."""
        self.stack.append(scene)
        self._entered()

    def pop(self):
        self.stack.pop()
        self._entered()

    def _entered(self):
        if self.top.music is not None:
            assets.music(self.top.music)
        self.top.enter()

    def update(self, dt, events):
        if self.pending:
            self.fade += dt / self.FADE_OUT
            if self.fade >= 1:
                self.fade = 1.0
                self.stack = [self.pending()]
                self.pending = None
                self._entered()
            return
        self.fade = max(0.0, self.fade - dt / self.FADE_IN)
        self.top.update(dt, events)

    def draw(self, screen):
        self.top.draw(screen)
        if self.fade > 0:
            self.black.set_alpha(int(255 * self.fade))
            screen.blit(self.black, (0, 0))
