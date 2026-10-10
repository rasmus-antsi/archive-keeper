"""The Scene base class and the SceneManager that runs a stack of them.

Scenes never touch each other; they ask the manager to go(), push() or pop().
"""
from . import assets, effects


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
    def __init__(self):
        self.stack = []
        self.pending = None       # a factory that builds the next scene once the screen is covered
        self.effect = "fade"      # which transition from game/effects.py is running
        self.fade = 1.0
        self.t = 0.0

    @property
    def top(self):
        return self.stack[-1]

    def start(self, scene):
        self.stack = [scene]
        self._entered()

    def go(self, factory, effect="fade"):
        """Cover the screen, replace the whole stack with factory(), uncover it again."""
        if self.pending is None:
            self.pending = factory
            self.effect = effect

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
        self.t += dt
        _, out, back = effects.EFFECTS[self.effect]
        if self.pending:
            self.fade += dt / out
            if self.fade >= 1:
                self.fade = 1.0
                self.stack = [self.pending()]
                self.pending = None
                self._entered()
            return
        self.fade = max(0.0, self.fade - dt / back)
        self.top.update(dt, events)

    def draw(self, screen):
        self.top.draw(screen)
        if self.fade > 0:
            effects.EFFECTS[self.effect][0](screen, self.fade, self.t, closing=self.pending is not None)
