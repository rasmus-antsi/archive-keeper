"""The Scene base class, the Overlay that opens on top of a scene, and the
SceneManager that runs a stack of them.

Scenes never touch each other; they ask the manager to go(), push() or pop().
"""
from . import assets, effects, ui


class Scene:
    music = None          # name of a track in assets/music, or None to leave it alone
    pausable = False      # whether Esc opens the pause menu here
    hushed = False        # whether the music is held down while this is on top
    plain = False         # True while it is drawn as the picture behind an overlay: no key prompts or hints

    def __init__(self, game):
        self.game = game
        self.state = game.state
        self.content = game.content
        self.scenes = game.scenes

    def enter(self):
        """Called when the scene becomes the top of the stack, also on return from an overlay."""

    def text(self, key, **values):
        """Interface text from data/game.json, see Content.text."""
        return self.content.text(key, **values)

    def hint(self, screen, key, **values):
        """The line of key help along the bottom edge, by its name in data/game.json."""
        if not self.plain:
            ui.hint(screen, self.text(key, **values))

    def update(self, dt, events):
        pass

    def draw(self, screen):
        pass


class Overlay(Scene):
    """Something that opens on top of a scene and shows it, darkened, behind itself:
    a shelf, a chest, the pause menu. It fades in over the scene below and out again.

    A subclass writes handle() and paint() instead of update() and draw(), paints its
    fixed parts on self.backdrop once, and calls close() when it is done.
    """
    DIM = 0.78                      # how dark the scene behind becomes
    OPEN, SHUT = 0.14, 0.10         # seconds to fade in and out

    def __init__(self, game):
        super().__init__(game)
        below = game.scenes.top
        below.plain = True
        below.draw(game.screen)                 # once more, without its key prompts and hints
        below.plain = False
        self.before = game.screen.copy()        # the scene below, as it looked
        self.backdrop = self.before.copy()      # the same, darkened
        effects.darken(self.backdrop, self.DIM)
        self.shown = 0.0                        # 0: not there yet, 1: fully open
        self.closing = False
        self.then = None

    def close(self, then=None):
        """Fade out and leave. then() runs once the scene below is back."""
        self.closing, self.then = True, then

    def handle(self, dt, events):
        """Keys and clicks while it is open."""

    def paint(self, screen):
        """Everything that goes on top of self.backdrop."""

    def update(self, dt, events):
        if not self.closing:
            self.shown = min(1.0, self.shown + dt / self.OPEN)
            self.handle(dt, events)
            return
        self.shown -= dt / self.SHUT
        if self.shown <= 0:
            self.scenes.pop()
            if self.then:
                self.then()

    def draw(self, screen):
        screen.blit(self.backdrop, (0, 0))
        self.paint(screen)
        if self.shown < 1:          # the scene below, fading away over it
            self.before.set_alpha(round(255 * (1 - effects.ease(self.shown))))
            screen.blit(self.before, (0, 0))


class SceneManager:
    def __init__(self):
        self.stack = []
        self.pending = None       # a factory that builds the next scene once the screen is covered
        self.effect = "fade"      # which transition from game/effects.py is running
        self.fade = 1.0           # how much of the screen the transition covers, 0..1
        self.still = None         # the picture of the scene that is being covered
        self.t = 0.0

    @property
    def top(self):
        return self.stack[-1]

    @property
    def busy(self):
        """True while the screen is being covered on the way to another scene."""
        return self.pending is not None

    def start(self, scene):
        self.stack = [scene]
        self._entered()

    def go(self, factory, effect="fade"):
        """Cover the screen, replace the whole stack with factory(), uncover it again.
        The scene is built while the screen is covered, so a slow start is never seen."""
        if self.pending is None:
            self.pending = factory
            self.effect = effect

    def push(self, scene):
        """Open an overlay on top of the current scene. Only the top scene is drawn and
        updated; an Overlay keeps a picture of what was below it."""
        self.stack.append(scene)
        self._entered()

    def pop(self):
        self.stack.pop()
        self._entered()

    def _entered(self):
        if self.top.music is not None:
            assets.music(self.top.music)
        assets.hush(self.top.hushed)
        self.top.enter()

    def update(self, dt, events):
        self.t += dt
        _, out, back = effects.EFFECTS[self.effect]
        if self.pending:
            self.fade += dt / out
            if self.fade >= 1:
                self.fade = 1.0
                self.stack = [self.pending()]
                self.pending = self.still = None
                self._entered()
            return
        self.fade = max(0.0, self.fade - dt / back)
        self.top.update(dt, events)

    def draw(self, screen):
        if self.still is not None:
            screen.blit(self.still, (0, 0))
        else:
            self.top.draw(screen)
            if self.pending:
                # a scene stands still while it is being covered, so it is drawn once and
                # the picture kept: the transition then has the whole frame to itself
                self.still = screen.copy()
        if self.fade > 0:
            effects.EFFECTS[self.effect][0](screen, self.fade, self.t, closing=self.pending is not None)
