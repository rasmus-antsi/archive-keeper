"""A memory, seen through the ghost's own eyes: one still picture, people who ask
for things, and objects to click. Everything about it comes from one file in
data/documents/.

The picture is assets/img/<background>, 1920x1080, and every rect and position in
the document is in those pixels. Until the picture exists the scene paints a plain
room and shows every object as a labelled box.

An object can have its own "sprite", drawn into its rect on top of the picture;
leave it out once the object is painted into the background.

An optional "establishing" picture (a wide view of the place) is shown first, until
a key or click. People can have a second "talk" image; the two alternate while they speak.
"""
import pygame

from .. import assets, settings, ui
from ..scene import Scene


class Memory(Scene):
    def __init__(self, game, doc):
        super().__init__(game)
        self.doc = doc
        self.music = doc.get("music", "memory")
        self.t = 0.0
        self.background = assets.backdrop(doc.get("background", ""))
        self.objects = [(o, pygame.Rect(o["rect"])) for o in doc["objects"]]
        self.npcs = [Npc(n) for n in doc.get("npcs", [])]
        self.request = 0               # which of the document's requests is being asked
        self.establishing = assets.backdrop(doc.get("establishing", ""))
        box = doc.get("dialogue", {})          # lets a document keep the text clear of a big portrait
        self.dialogue = ui.DialogueBox(box.get("x", 180), box.get("width", settings.W - 360))
        self.hover = None
        self.blackout = 0.0            # a wrong guess blinks the scene away for a moment
        self.black = pygame.Surface((settings.W, settings.H))
        self.done = False

    def enter(self):
        if not self.establishing:
            self.ask()

    # ---------------------------------------------------------------- rules

    def speaker(self, request):
        npc = next((n for n in self.npcs if n.id == request.get("speaker")), self.npcs[0] if self.npcs else None)
        return npc.name if npc else ""

    def ask(self, first=None):
        """The current request's hint, optionally after some other lines."""
        request = self.doc["requests"][self.request]
        self.dialogue.say(list(first or []) + request["hint"], self.speaker(request))

    def choose(self, obj):
        request = self.doc["requests"][self.request]
        if obj["id"] != request["target"]:
            assets.play("wrong.ogg", 0.5)
            self.blackout = 1.0
            self.ask(first=self.doc.get("retry", []))
            return
        assets.play("restore.ogg", 0.5)
        self.request += 1
        if self.request < len(self.doc["requests"]):
            self.ask(first=request.get("thanks", []))
        else:
            self.done = True
            self.dialogue.say(request.get("thanks", []) or ["…"], self.speaker(request), on_done=self.leave)

    def leave(self):
        if self.done:
            self.state.solved.add(self.doc["id"])
        from .archive import Archive
        self.scenes.go(lambda: Archive(self.game), "spiral")

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        self.blackout = max(0.0, self.blackout - dt / 0.7)
        self.hover = None
        if self.establishing:
            if self.t > 0.8 and (ui.confirm(events) or ui.clicked(events)):
                self.establishing = None
                self.t = 0.0
                self.ask()
            return
        if self.blackout > 0.5:
            return
        if self.dialogue.update(dt, events):
            return
        if ui.pressed(events, *ui.BACK):
            self.leave()
            return
        mouse = self.game.display.mouse()
        self.hover = next((o for o, rect in self.objects if rect.collidepoint(mouse)), None)
        click = ui.clicked(events)
        if click:
            if any(n.rect.collidepoint(click) for n in self.npcs):
                self.ask()
                return
            obj = next((o for o, rect in self.objects if rect.collidepoint(click)), None)
            if obj:
                self.choose(obj)

    # ---------------------------------------------------------------- drawing

    def draw(self, screen):
        if self.establishing:
            screen.blit(self.establishing, (0, 0))
            ui.draw_text(screen, self.doc.get("place", ""), (settings.W / 2, 110), "title", 96, settings.CREAM, center=True)
            ui.hint(screen, "space — continue")
            return
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((70, 60, 56))
            pygame.draw.rect(screen, (96, 78, 62), (0, 675, settings.W, 405))
            for obj, rect in self.objects:
                if obj.get("sprite"):
                    continue
                pygame.draw.rect(screen, (150, 130, 104), rect)
                pygame.draw.rect(screen, (50, 40, 34), rect, 6)
                ui.draw_text(screen, obj.get("label", obj["id"]), rect.center, "mono", 20, settings.INK, center=True)
        for obj, rect in self.objects:
            if obj.get("sprite"):
                img = assets.optional(obj["sprite"])
                if img:
                    screen.blit(assets.sprite(obj["sprite"], scale=max(1, rect.height // img.get_height())), rect)
        if self.hover:
            pygame.draw.rect(screen, settings.CREAM, pygame.Rect(self.hover["rect"]).inflate(20, 20), 4, border_radius=8)
        for npc in self.npcs:
            npc.draw(screen, mouth_open=self.dialogue.talking == npc.name and int(self.t * 9) % 2 == 0)

        fade = max(0, min(1, self.t / 0.6, (5 - self.t) / 1.0))
        if fade > 0:
            ui.draw_text(screen, self.doc.get("place", ""), (settings.W / 2, 110), "title", 96, settings.CREAM,
                         center=True, alpha=int(255 * fade))
        n, total = min(self.request + 1, len(self.doc["requests"])), len(self.doc["requests"])
        ui.draw_text(screen, f"{self.doc['title']}  ·  {n} / {total}", (40, 24), "mono", 26, settings.CREAM)
        if self.dialogue.active:
            self.dialogue.draw(screen)
        else:
            ui.hint(screen, "click the thing they asked for · click a person to hear it again · Esc — back to the archive")
        if self.blackout > 0:
            self.black.set_alpha(int(255 * min(1, self.blackout * 2)))
            screen.blit(self.black, (0, 0))


class Npc:
    """A person in the picture. With a sprite it is drawn at pos (feet); without one
    it is already painted into the background and only needs a clickable rect."""

    def __init__(self, data):
        self.id = data["id"]
        self.name = data.get("name", "")
        self.img = None
        self.talk = None                       # the same picture with the mouth open
        if data.get("sprite"):
            self.img = assets.sprite(data["sprite"], scale=data.get("scale"))
            self.rect = self.img.get_rect(midbottom=data["pos"])
            if assets.optional(data.get("talk", "")):
                self.talk = assets.sprite(data["talk"], scale=data.get("scale"))
        else:
            self.rect = pygame.Rect(data["rect"])

    def draw(self, screen, mouth_open=False):
        if self.img:
            screen.blit(self.talk if mouth_open and self.talk else self.img, self.rect)
