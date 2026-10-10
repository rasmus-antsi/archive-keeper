"""The Scene base class and the SceneManager that runs a stack of them.

A scene draws twice: draw() onto the small pixel canvas and draw_ui() onto
the full-size window for text and photos. Scenes never touch each other;
they ask the manager to go(), push() or pop().
"""
import pygame

from . import assets, settings


class Scene:
    music = None          # name of a track in assets/music, or None to leave it alone
    see_through = False   # True for overlays: the scene below is still drawn

    def __init__(self, game):
        self.game = game
        self.state = game.state
        self.content = game.content
        self.scenes = game.scenes

    def enter(self):
        """Called when the scene becomes the top of the stack, also on return from an overlay."""

    def update(self, dt, events):
        pass

    def draw(self, canvas):
        pass

    def draw_ui(self, screen):
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
        """Open an overlay on top of the current scene, without a fade."""
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

    def _visible(self):
        first = len(self.stack) - 1
        while first > 0 and self.stack[first].see_through:
            first -= 1
        return self.stack[first:]

    def draw(self, canvas, screen):
        visible = self._visible()
        canvas.fill(settings.NIGHT)
        for scene in visible:
            scene.draw(canvas)
        pygame.transform.scale(canvas, (settings.W, settings.H), screen)
        for scene in visible:
            scene.draw_ui(screen)
        if self.fade > 0:
            self.black.set_alpha(int(255 * self.fade))
            screen.blit(self.black, (0, 0))
