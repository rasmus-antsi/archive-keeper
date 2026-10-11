"""A memory: a place from the past, larger than the screen, that the ghost walks
around in. Somebody there asks for a thing. The ghost searches chests, cupboards
and houses for it, takes it and carries it back.

Everything about a memory is in one file in data/documents/:

  map       the place (see game/world.py). A prop with "holds": [item ids] can be
            opened and searched; give it a "label".
  items     everything that can be found: {"id", "label", "image" or "icon"}.
            "image" is a drawn picture in assets/img; "icon" names a stand-in.
  npcs      the people: a small "sprite" standing at "pos", and optionally a big
            "portrait" (with a mouth-open "portrait_talk") shown while they speak.
  requests  what is asked for, in order: {"speaker", "hint", "target", "thanks"}.

An optional "establishing" picture (a wide view of the place) is shown first, until
a key or click.
"""
import pygame

from .. import assets, effects, paint, settings, ui
from ..player import Player
from ..scene import Scene


class Memory(Scene):
    pausable = True

    def __init__(self, game, doc):
        super().__init__(game)
        self.doc = doc
        self.music = doc.get("music", "memory")
        self.t = 0.0
        self.world = game.world(doc["id"], doc["map"])
        self.player = Player(doc["map"]["start"])
        self.world.look_at(self.player.pos)
        self.items = {i["id"]: i for i in doc["items"]}
        self.containers = [p for p in self.world.props if "holds" in p.data]
        self.home = {item: p.id for p in self.containers for item in p.data["holds"]}     # where each thing belongs
        self.where = dict(self.home)                                                     # where it is now
        self.carrying = None
        self.npcs = [Npc(n) for n in doc.get("npcs", [])]
        self.request = 0               # which of the document's requests is being asked
        self.establishing = assets.backdrop(doc.get("establishing", ""))
        box = doc.get("dialogue", {})          # lets a document keep the text clear of a big portrait
        self.dialogue = ui.DialogueBox(box.get("x", 180), box.get("width", settings.W - 360), prompt=self.text("advance"))
        self.near = None               # the container or Npc the ghost is standing at
        self.blackout = 0.0            # a wrong guess blinks the scene away for a moment
        self.done = False
        self.asked = False

    def enter(self):
        if not self.establishing and not self.asked:
            self.ask()

    # ---------------------------------------------------------------- rules

    def speaker(self, request):
        return next((n for n in self.npcs if n.id == request.get("speaker")), self.npcs[0] if self.npcs else None)

    def ask(self, first=None):
        """The current request's hint, optionally after some other lines."""
        self.asked = True
        request = self.doc["requests"][self.request]
        npc = self.speaker(request)
        self.dialogue.say(list(first or []) + request["hint"], npc.name if npc else "")

    def contents(self, container):
        return [self.items[i] for i in container.data["holds"] if self.where.get(i) == container.id]

    def take(self, item):
        """Pick a thing up; whatever was being carried goes back where it belongs."""
        if self.carrying:
            self.where[self.carrying] = self.home[self.carrying]
        self.carrying = item["id"]
        del self.where[item["id"]]
        assets.play("place.ogg", 0.6)

    def give(self):
        request = self.doc["requests"][self.request]
        npc = self.speaker(request)
        item, self.carrying = self.carrying, None
        if item != request["target"]:
            self.where[item] = self.home[item]
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
            self.dialogue.say(request.get("thanks", []) or ["…"], npc.name if npc else "", on_done=self.leave)

    def leave(self):
        """Back to the archive: with the memory restored, or given up from the pause menu."""
        if self.done:
            self.state.solved.add(self.doc["id"])
        from .archive import Archive
        self.scenes.go(lambda: Archive(self.game), "spiral")

    def walkable(self, feet):
        return self.world.walkable(feet) and feet.collidelist([n.solid for n in self.npcs]) < 0

    def nearest(self):
        feet = self.player.feet()
        here = self.world.indoors(feet.center)       # nobody is talked to through a wall
        npc = next((n for n in self.npcs if n.solid.inflate(18, 18).colliderect(feet)
                    and self.world.indoors(n.solid.center) is here), None)
        return npc or self.world.nearest(feet, self.containers)

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        self.blackout = max(0.0, self.blackout - dt / 0.7)
        self.world.update(dt, self.player.pos)
        if self.establishing:
            if self.t > 0.8 and (ui.confirm(events) or ui.clicked(events)):
                self.establishing = None
                self.t = 0.0
                self.ask()
            return
        busy = self.blackout > 0.5 or self.dialogue.update(dt, events)
        self.player.update(dt, self.walkable, control=not busy)
        self.world.look_at(self.player.pos, dt)
        if busy:
            self.near = None
            return
        self.near = self.nearest()
        if ui.confirm(events) and self.near:
            if not isinstance(self.near, Npc):
                self.look_inside(self.near)
            elif self.carrying:
                self.give()
            else:
                self.ask()

    def look_inside(self, container):
        from .inside import Inside
        assets.play(f"page{1 + int(self.t * 7) % 6}.ogg", 0.5)
        self.near = None
        self.scenes.push(Inside(self.game, self, container))

    # ---------------------------------------------------------------- drawing

    def draw(self, screen):
        if self.establishing:
            screen.blit(self.establishing, (0, 0))
            ui.draw_text(screen, self.doc.get("place", ""), (settings.W / 2, 110), "title", 96, settings.CREAM, center=True)
            self.hint(screen, "memory.continue")
            return
        outlines = [(self.near.rect, settings.CREAM)] if self.near and not isinstance(self.near, Npc) else []
        self.world.draw(screen, self.player, [n.actor() for n in self.npcs], outlines=outlines)
        talking = self.dialogue.active and self.dialogue.queue[0][0]
        for npc in self.npcs:
            if talking == npc.name:
                npc.draw_portrait(screen, mouth_open=self.dialogue.talking == npc.name and int(self.t * 9) % 2 == 0)

        fade = max(0, min(1, self.t / 0.6, (5 - self.t) / 1.0))
        if fade > 0:
            ui.draw_text(screen, self.doc.get("place", ""), (settings.W / 2, 110), "title", 96, settings.CREAM,
                         center=True, alpha=int(255 * fade))
        n, total = min(self.request + 1, len(self.doc["requests"])), len(self.doc["requests"])
        ui.label(screen, f"{self.doc['title']}  ·  {n} / {total}", (24, 14))
        if self.carrying:
            item = self.items[self.carrying]
            ui.panel(screen, (settings.W - 200, 20, 176, 216), alpha=200, border=settings.WARM)
            img = item_image(item, 128)
            screen.blit(img, img.get_rect(center=(settings.W - 112, 104)))
            ui.draw_text(screen, self.text("memory.carrying"), (settings.W - 112, 196), "mono", 24, settings.WARM,
                         center=True)
        if self.dialogue.active:
            self.dialogue.draw(screen)
        elif not self.plain:
            self.draw_prompts(screen)
        effects.darken(screen, self.blackout * 2)

    def draw_prompts(self, screen):
        """What can be done right here: a key cap on the thing, a line of help, and an arrow
        back to whoever is waiting for what the ghost carries."""
        if isinstance(self.near, Npc):
            ui.key_prompt(screen, self.world.to_screen(self.near.rect.midtop))
            if self.carrying:
                self.hint(screen, "memory.give", item=self.items[self.carrying]["label"])
            else:
                self.hint(screen, "memory.listen")
        elif self.near:
            ui.key_prompt(screen, self.world.to_screen(self.near.rect.midtop))
            self.hint(screen, "memory.open", thing=self.near.label)
        else:
            if self.carrying and self.npcs:
                asker = self.speaker(self.doc["requests"][min(self.request, len(self.doc["requests"]) - 1)])
                ui.pointer(screen, self.world.to_screen(asker.rect.center), settings.WARM)
            self.hint(screen, "memory.search")


_icons = {}


def warm_up(doc):
    """Make the people of a memory ahead of time, behind the loading bar: enlarging a big
    portrait takes long enough to be felt if it is left until the memory opens."""
    for npc in doc.get("npcs", []):
        Npc(npc)


def item_image(item, box):
    """An item's picture enlarged with hard edges to fit a square of box pixels."""
    name = item.get("image") or ""
    if assets.optional(name):
        img = assets.optional(name)
        return assets.sprite(name, scale=max(1, min(box // img.get_width(), box // img.get_height())))
    key = ("icon", item.get("icon", item["id"]), box)
    if key not in _icons:
        _icons[key] = assets.enlarge(paint.icon(item.get("icon", item["id"])), box // 16)
    return _icons[key]


class Npc:
    """A person standing in the place, at pos (the feet)."""

    def __init__(self, data):
        self.id = data["id"]
        self.name = data.get("name", "")
        self.img = assets.optional(data.get("sprite", "")) or paint.robot()
        self.rect = self.img.get_rect(midbottom=data["pos"])
        self.solid = pygame.Rect(self.rect.left + 1, self.rect.bottom - 5, self.rect.width - 2, 5)
        self.portrait = self.portrait_talk = None
        if assets.optional(data.get("portrait", "")):
            k = data.get("portrait_scale")
            self.portrait = assets.sprite(data["portrait"], scale=k)
            talk = data.get("portrait_talk", "")
            self.portrait_talk = assets.sprite(talk, scale=k) if assets.optional(talk) else self.portrait
            self.portrait_pos = data.get("portrait_pos", (1560, settings.H))

    def actor(self):
        return self.rect.bottom, self.img, self.rect.topleft

    def draw_portrait(self, screen, mouth_open=False):
        if self.portrait:
            img = self.portrait_talk if mouth_open else self.portrait
            screen.blit(img, img.get_rect(midbottom=self.portrait_pos))
