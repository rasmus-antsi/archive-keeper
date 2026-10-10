"""A memory: a small place from the past that the ghost walks around in, seen from
above like the archive room. People there ask for things; the ghost walks up to
an object and presses E to hand it over. Everything about it comes from one file
in data/documents/.

The picture is assets/img/<background>, 1920x1080, and every rect and position in
the document is in those pixels. "floor" is where the ghost can walk and "start"
where it appears; objects and people block the way. Until the picture exists the
scene paints a plain room and shows every object as a labelled box.

An object can have its own "sprite", drawn into its rect on top of the picture;
leave it out once the object is painted into the background.

A person has a small "sprite" standing in the room and, optionally, a big
"portrait" (with a mouth-open "portrait_talk") that appears while they speak.

An optional "establishing" picture (a wide view of the place) is shown first, until
a key or click.
"""
import pygame

from .. import assets, settings, ui
from ..player import Player
from ..scene import Scene

REACH = 60                     # how close to a thing counts as standing at it


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
        self.floor = pygame.Rect(doc.get("floor", (144, 300, 1632, 672)))
        self.player = Player(doc.get("start", self.floor.center), "up")
        self.near = None               # the object dict or Npc the ghost is standing at
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

    def walkable(self, feet):
        return self.floor.contains(feet) and feet.collidelist([rect for _, rect in self.objects]) < 0 \
            and feet.collidelist([n.feet for n in self.npcs]) < 0

    def nearest(self):
        """The object or person the ghost is standing at, the closest one if there are several."""
        feet = self.player.feet()
        things = [(o, rect) for o, rect in self.objects] + [(n, n.rect) for n in self.npcs]
        close = [(pygame.Vector2(feet.center).distance_to(rect.center), i) for i, (_, rect) in enumerate(things)
                 if rect.inflate(REACH * 2, REACH * 2).colliderect(feet)]
        return things[min(close)[1]][0] if close else None

    def leave(self):
        if self.done:
            self.state.solved.add(self.doc["id"])
        from .archive import Archive
        self.scenes.go(lambda: Archive(self.game), "spiral")

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        self.blackout = max(0.0, self.blackout - dt / 0.7)
        if self.establishing:
            if self.t > 0.8 and (ui.confirm(events) or ui.clicked(events)):
                self.establishing = None
                self.t = 0.0
                self.ask()
            return
        if self.blackout > 0.5 or self.dialogue.update(dt, events):
            self.player.update(dt, self.walkable, control=False)
            self.near = None
            return
        if ui.pressed(events, *ui.BACK):
            self.leave()
            return
        self.player.update(dt, self.walkable)
        self.near = self.nearest()
        if ui.confirm(events) and self.near:
            if isinstance(self.near, Npc):
                self.ask()
            else:
                self.choose(self.near)

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
            screen.fill((34, 30, 34))
            pygame.draw.rect(screen, (70, 60, 56), (self.floor.left, 48, self.floor.width, self.floor.top - 48))
            pygame.draw.rect(screen, (112, 94, 76), self.floor)
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
        if self.near and not isinstance(self.near, Npc):
            pygame.draw.rect(screen, settings.CREAM, pygame.Rect(self.near["rect"]).inflate(20, 20), 4, border_radius=8)
        # whoever stands lower on the screen is drawn in front
        people = [(n.rect.bottom, lambda n=n: n.draw(screen)) for n in self.npcs]
        people.append((self.player.pos.y, lambda: self.player.draw(screen)))
        for _, draw in sorted(people, key=lambda pair: pair[0]):
            draw()
        for npc in self.npcs:
            if self.dialogue.active and self.dialogue.queue[0][0] == npc.name:
                npc.draw_portrait(screen, mouth_open=self.dialogue.talking == npc.name and int(self.t * 9) % 2 == 0)

        fade = max(0, min(1, self.t / 0.6, (5 - self.t) / 1.0))
        if fade > 0:
            ui.draw_text(screen, self.doc.get("place", ""), (settings.W / 2, 110), "title", 96, settings.CREAM,
                         center=True, alpha=int(255 * fade))
        n, total = min(self.request + 1, len(self.doc["requests"])), len(self.doc["requests"])
        ui.draw_text(screen, f"{self.doc['title']}  ·  {n} / {total}", (40, 24), "mono", 26, settings.CREAM)
        if self.dialogue.active:
            self.dialogue.draw(screen)
        else:
            if isinstance(self.near, Npc):
                ui.hint(screen, "E — hear it again")
            elif self.near:
                ui.hint(screen, f"E — hand over: {self.near.get('label', self.near['id'])}")
            else:
                ui.hint(screen, "walk to the thing they asked for and press E · Esc — back to the archive")
        if self.blackout > 0:
            self.black.set_alpha(int(255 * min(1, self.blackout * 2)))
            screen.blit(self.black, (0, 0))


class Npc:
    """A person in the room. With a sprite it stands at pos (feet); without one it
    is already painted into the background and only needs a rect."""

    def __init__(self, data):
        self.id = data["id"]
        self.name = data.get("name", "")
        self.img = assets.sprite(data["sprite"], scale=data.get("scale")) if data.get("sprite") else None
        self.rect = self.img.get_rect(midbottom=data["pos"]) if self.img else pygame.Rect(data["rect"])
        self.feet = pygame.Rect(self.rect.left, self.rect.bottom - 40, self.rect.width, 40)
        self.portrait = self.portrait_talk = None
        if assets.optional(data.get("portrait", "")):
            k = data.get("portrait_scale")
            self.portrait = assets.sprite(data["portrait"], scale=k)
            talk = data.get("portrait_talk", "")
            self.portrait_talk = assets.sprite(talk, scale=k) if assets.optional(talk) else self.portrait
            self.portrait_pos = data.get("portrait_pos", (1560, settings.H))

    def draw(self, screen):
        if self.img:
            screen.blit(self.img, self.rect)

    def draw_portrait(self, screen, mouth_open=False):
        if self.portrait:
            img = self.portrait_talk if mouth_open else self.portrait
            screen.blit(img, img.get_rect(midbottom=self.portrait_pos))
