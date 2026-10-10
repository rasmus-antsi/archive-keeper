"""A trip into a record: a place and a day, with people to overhear and things to haunt.

Everything about a trip lives in data/levels/<id>.json. Flags are plain words;
people change place and lines when their "when" flags are set, haunting an
object sets a flag, and events play short scenes once their flags are all set.
"""
import json
import math

import pygame

from . import core
from .ghost import Ghost

INK = (58, 42, 34)


def bubble(text, name=""):
    """A speech bubble surface with a small tail at the bottom centre."""
    lines = core.wrap(text, "serif", 20, 300)
    widths = [core.text(l, "serif", 20, INK).get_width() for l in lines]
    if name:
        widths.append(core.text(name, "mono", 13, (150, 96, 70)).get_width())
    w = max(widths) + 30
    h = len(lines) * 25 + 20 + (18 if name else 0)
    surf = pygame.Surface((w, h + 14), pygame.SRCALPHA)
    pygame.draw.rect(surf, (60, 40, 30, 90), (2, 4, w - 2, h), border_radius=14)
    pygame.draw.rect(surf, (252, 244, 224), (0, 0, w - 2, h - 2), border_radius=14)
    pygame.draw.polygon(surf, (252, 244, 224), [(w / 2 - 10, h - 4), (w / 2 + 10, h - 4), (w / 2, h + 12)])
    y = 9
    if name:
        surf.blit(core.text(name, "mono", 13, (150, 96, 70)), (15, y))
        y += 18
    for l in lines:
        surf.blit(core.text(l, "serif", 20, INK), (15, y))
        y += 25
    return surf


class Stage:
    """A scrolling place the ghost floats around in. Home and trips both build on it."""

    def __init__(self, game, map_name, size, start, control=True):
        self.game = game
        self.t = 0.0
        self.control = control
        self.map = core.image(map_name, scale=1).convert()
        self.size = size
        self.ghost = Ghost(start)
        self.cam = self.cam_target()
        self.box = core.TextBox()
        self.queue = []                    # (text, speaker, hold) waiting for the box
        self.floaters = []
        self.motes = core.Motes(10, (255, 232, 190))
        self.toast = None

    def walkable(self, p):
        return True

    def cam_target(self):
        x = max(0, min(self.size[0] - core.W, self.ghost.pos.x - core.W / 2))
        y = max(0, min(self.size[1] - core.H, self.ghost.pos.y - 30 - core.H / 2))
        return pygame.Vector2(x, y)

    def say(self, text, speaker=""):
        self.queue.append((text, speaker, core.WAIT))

    def say_now(self, text, speaker=""):
        self.queue.clear()
        self.box.say(text, speaker, core.WAIT)

    def advance(self, events):
        """The text box waits for a key. Returns True if the press was used up."""
        if self.box.string and core.pressed_confirm(events):
            if self.box.shown < len(self.box.string):
                self.box.shown = len(self.box.string)
            else:
                self.box.clear()
            return True
        return False

    def step(self, dt):
        self.t += dt
        mouse_world = pygame.Vector2(pygame.mouse.get_pos()) + self.cam
        self.ghost.update(dt, self.control, mouse_world, self.walkable)
        self.cam += (self.cam_target() - self.cam) * min(1.0, 5 * dt)
        self.motes.update(dt)
        self.box.update(dt)
        if not self.box.string and self.queue:
            self.box.say(*self.queue.pop(0))
        for f in self.floaters:
            f[2] += dt
        self.floaters = [f for f in self.floaters if f[2] < 1.8]
        if self.toast:
            self.toast[2] += dt
            if self.toast[2] > 4.5:
                self.toast = None

    def draw_map(self, surf):
        cam = (round(self.cam.x), round(self.cam.y))
        surf.blit(self.map, (0, 0), pygame.Rect(cam, (core.W, core.H)))
        return cam

    def draw_over(self, surf, cam):
        self.motes.draw(surf)
        for value, pos, age in self.floaters:
            k = core.ease(age / 1.2)
            img = core.text(f"+ {value}", "bold", 24, core.CREAM)
            back = core.panel((img.get_width() + 24, img.get_height() + 10), (70, 44, 30), int(220 * (1 - max(0, age - 1.3) / 0.5)))
            at = (pos.x - cam[0], pos.y - 90 - 50 * k - cam[1])
            surf.blit(back, back.get_rect(center=at))
            surf.blit(img, img.get_rect(center=at))
        if self.toast:
            title, sub, age = self.toast
            a = int(255 * max(0, min(1, age / 0.5, (4.5 - age) / 0.8)))
            core.draw_text(surf, title, (core.W / 2, 96), "bold", 46, core.CREAM, center=True, alpha=a)
            core.draw_text(surf, sub, (core.W / 2, 138), "italic", 23, core.CREAM, center=True, alpha=a)
        self.box.draw(surf)


class Npc:
    HEAR = 115

    def __init__(self, data):
        self.id = data["id"]
        self.name = data.get("name", "")
        self.sees = data.get("sees", False)
        self.img = core.image(data["sprite"], scale=1)
        self.states = data["states"]
        self.cur = None
        self.pos = pygame.Vector2(self.states[0]["pos"])
        self.path = []
        self.speed = 80
        self.line_i = 0
        self.listen = 0.0
        self.away = True               # the ghost has left since the last round of lines
        self.bubble = None             # [surface, seconds left, total]
        self.phase = hash(self.id) % 7

    def pick_state(self, flags):
        best = self.states[0]
        for st in self.states:
            if all(f in flags for f in st.get("when", [])):
                best = st
        return best

    def say(self, text, seconds=None):
        self.bubble = [bubble(text, self.name), seconds or 1.8 + len(text) * 0.06, 0.0]

    def unheard(self):
        return self.line_i < len(self.cur.get("lines", []))

    def update(self, dt, level):
        st = self.pick_state(level.flags)
        if st is not self.cur:
            first = self.cur is None
            self.cur = st
            self.path = [] if first else [pygame.Vector2(p) for p in st.get("path", [])] + [pygame.Vector2(st["pos"])]
            self.speed = st.get("speed", 80)
            self.line_i, self.away = 0, True
            if first:
                self.pos = pygame.Vector2(st["pos"])
        if self.path:
            to = self.path[0] - self.pos
            if to.length() < 4:
                self.path.pop(0)
            else:
                self.pos += to.normalize() * min(self.speed * dt, to.length())
                self.phase += dt * 9
        if self.bubble:
            self.bubble[1] -= dt
            self.bubble[2] += dt
            if self.bubble[1] <= 0:
                self.bubble = None
            return
        # overheard: stay close for a moment and they say their next line
        lines = self.cur.get("lines", [])
        near = self.pos.distance_to(level.ghost.pos) < self.HEAR
        if not near:
            self.away, self.listen = True, 0.0
            if self.line_i >= len(lines):
                self.line_i = len(lines)      # nothing new until the state changes
            return
        if level.listen_to is not self:
            self.listen = min(self.listen, 0.0)
            return
        if self.line_i >= len(lines):
            if not self.away:
                return
            self.line_i = 0                   # came back: they repeat themselves
        self.listen += dt
        if self.listen > 0.45:
            self.listen = -0.4
            self.away = False
            line = lines[self.line_i]
            self.line_i += 1
            if isinstance(line, str):
                line = {"text": line}
            self.say(line["text"])
            level.apply(line, self.pos)

    def draw(self, surf, cam):
        x, y = self.pos.x - cam[0], self.pos.y - cam[1]
        bob = abs(math.sin(self.phase)) * 3 if self.path else 0
        surf.blit(self.img, self.img.get_rect(midbottom=(x, y - bob)))

    def draw_bubble(self, surf, cam, t):
        x, y = self.pos.x - cam[0], self.pos.y - cam[1] - self.img.get_height() - 4
        if self.bubble:
            img, left, age = self.bubble
            k = min(1.0, age / 0.15, left / 0.25)
            if k < 1:
                img = img.copy()
                img.set_alpha(int(255 * k))
            rect = img.get_rect(midbottom=(x, y + (1 - k) * 8))
            rect.clamp_ip(pygame.Rect(8, 8, core.W - 16, core.H - 16))
            surf.blit(img, rect)
        elif self.unheard() and not self.path:
            # three small dots: this person has something you have not heard
            by = y + 6 + math.sin(t * 3 + self.phase) * 3
            pygame.draw.circle(surf, (252, 244, 224), (x, by), 13)
            for dx in (-6, 0, 6):
                pygame.draw.circle(surf, (150, 96, 70) if not self.sees else (70, 150, 140), (x + dx, by), 2)


class Haunt:
    REACH = 100

    def __init__(self, data):
        self.data = data
        self.id = data["id"]
        self.pos = pygame.Vector2(data["pos"])
        self.at = pygame.Vector2(data.get("at", data["pos"]))
        self.sprites = [core.image(s, scale=1) for s in data.get("sprite", [])]
        self.shake = 0.0

    def done(self, flags):
        return "set" in self.data and self.data["set"] in flags

    def draw(self, surf, cam, flags, t):
        x, y = self.at.x - cam[0], self.at.y - cam[1]
        wob = math.sin(t * 50) * 5 * self.shake
        if self.sprites:
            img = self.sprites[1 if self.done(flags) and len(self.sprites) > 1 else 0]
            surf.blit(img, img.get_rect(center=(x + wob, y)))
        if self.shake:
            core.add_glow(surf, (x, y), 110, core.TEAL, self.shake)


class Level(Stage):
    def __init__(self, game, level_id):
        with open(f"data/levels/{level_id}.json", encoding="utf-8") as f:
            self.data = data = json.load(f)
        super().__init__(game, data["map"], data["size"], data["start"])
        self.id = level_id
        self.rec = game.by_id[data["record"]]
        self.flags = game.flags.setdefault(level_id, set())
        self.walk = [(pygame.Rect(w["rect"]), w.get("when", [])) for w in data["walk"]]
        self.npcs = [Npc(n) for n in data["npcs"]]
        self.by_id = {n.id: n for n in self.npcs}
        self.haunts = [Haunt(h) for h in data.get("haunts", [])]
        self.events = data.get("events", [])
        self.wait = {}                     # event id -> seconds its conditions have held
        self.event = None                  # [event, step index, seconds left]
        self.haunting = None               # [haunt, seconds]
        self.listen_to = None              # the one person the ghost is overhearing right now
        self.exit = core.Hotspot(data["exit"], 84, repeat=True, linger=1.0)
        self.toast = [data["title"], data["sub"], 0.0]
        for npc in self.npcs:
            npc.update(0, self)
        if "arrived" not in self.flags:
            self.flags.add("arrived")
            for line in data.get("intro", []):
                self.say(line)

    # ---------------------------------------------------------------- rules

    def walkable(self, p):
        return any(r.collidepoint(p) for r, when in self.walk if all(f in self.flags for f in when))

    def facts(self):
        return [f for f in self.game.fragments if f["rid"] == self.rec["id"]]

    def complete(self):
        return all(f["state"] != "world" for f in self.facts())

    def apply(self, what, pos):
        """A line or event step may hand over a fact or set a flag."""
        if "set" in what:
            self.flags.add(what["set"])
        if "fact" in what:
            f = self.facts()[what["fact"]]
            if f["state"] == "world":
                f["state"] = "held"
                core.play(f"chime_{2 + what['fact']}.ogg", 0.6)
                self.game.remember(self.rec["blanks"][what["fact"]]["label"], f["value"])
                self.floaters.append([f["value"], pygame.Vector2(pos), 0.0])
                if self.complete():
                    self.say("Kõik on meeles. Värav, kust ma tulin, helendab: sealt saab tagasi serverisse.")

    def nearest_haunt(self):
        best = None
        for h in self.haunts:
            if h.done(self.flags) and not h.data.get("repeat"):
                continue
            d = h.pos.distance_to(self.ghost.pos)
            if d < Haunt.REACH and (best is None or d < best[0]):
                best = (d, h)
        return best[1] if best else None

    # ---------------------------------------------------------------- update

    def update(self, dt, events):
        self.step(dt)
        # one voice at a time: the nearest person, those with something new first
        self.listen_to = None
        if not self.event and not any(n.bubble for n in self.npcs):
            near = [n for n in self.npcs if n.cur.get("lines") and not n.path
                    and n.pos.distance_to(self.ghost.pos) < Npc.HEAR]
            if near:
                self.listen_to = min(near, key=lambda n: (not n.unheard(), n.pos.distance_to(self.ghost.pos)))
        for npc in self.npcs:
            npc.update(dt, self)

        if self.haunting:
            h, left = self.haunting
            left -= dt
            h.shake = max(0.0, min(1.0, left / 0.3, (0.9 - left) / 0.2))
            self.ghost.pos += (h.at - self.ghost.pos) * min(1.0, 10 * dt)
            if left <= 0:
                h.shake = 0.0
                self.ghost.hidden = False
                self.ghost.pos = pygame.Vector2(h.pos)
                self.haunting = None
                if "set" in h.data:
                    self.flags.add(h.data["set"])
                self.say_now(h.data["text"])
            else:
                self.haunting[1] = left
            return

        self.run_events(dt)
        used = self.advance(events)
        target = self.nearest_haunt()
        if target and not used and core.pressed_confirm(events):
            core.play("hum.ogg", 0.8)
            self.ghost.hidden = True
            self.ghost.vel.update(0, 0)
            self.haunting = [target, 0.9]
        if self.complete() and self.exit.update(dt, self.ghost.pos):
            core.play("enter.ogg", 0.6)
            self.leave()
        if core.pressed(events, pygame.K_ESCAPE):
            self.leave()

    def leave(self):
        """Back to the server, with whatever was learned kept in memory."""
        for f, blank in zip(self.facts(), self.rec["blanks"]):
            if f["state"] != "world":
                self.game.remember(blank["label"], f["value"])
        from .desk import Desk
        self.game.go(lambda: Desk(self.game, open_file=self.game.case_file(self.rec["id"])))

    def run_events(self, dt):
        if self.event:
            ev, i, left = self.event
            left -= dt
            if left <= 0:
                i += 1
                if i >= len(ev["script"]):
                    self.flags.add(ev["set"])
                    self.event = None
                    return
                step = ev["script"][i]
                npc = self.by_id[step["who"]]
                npc.say(step["text"], step["t"])
                self.apply(step, npc.pos)
                left = step["t"] + 0.3
            self.event = [ev, i, left]
            return
        for ev in self.events:
            if ev["set"] in self.flags or not all(f in self.flags for f in ev["when"]):
                continue
            self.wait[ev["id"]] = self.wait.get(ev["id"], 0.0) + dt
            if self.wait[ev["id"]] >= ev.get("delay", 0):
                for npc in self.npcs:
                    npc.bubble = None
                self.event = [ev, -1, 0.0]
            return

    # ---------------------------------------------------------------- draw

    def draw(self, surf):
        cam = self.draw_map(surf)
        if self.complete():
            ex = (self.exit.pos.x - cam[0], self.exit.pos.y - cam[1])
            core.add_glow(surf, ex, 150, core.TEAL, 0.5 + 0.2 * math.sin(self.t * 2.4))
            pygame.draw.rect(surf, core.CREAM, pygame.Rect(ex[0] - 34, ex[1] - 60, 68, 90), 3, border_radius=8)
            self.exit.draw(surf, core.TEAL, cam)
        things = [(n.pos.y, n) for n in self.npcs] + [(self.ghost.pos.y + 30, self.ghost)]
        for h in self.haunts:
            things.append((h.at.y + 30, h))
        for _, thing in sorted(things, key=lambda t: t[0]):
            if isinstance(thing, Haunt):
                thing.draw(surf, cam, self.flags, self.t)
            else:
                thing.draw(surf, cam)
        for npc in self.npcs:
            npc.draw_bubble(surf, cam, self.t)

        target = None if self.haunting or self.event else self.nearest_haunt()
        if target:
            x, y = target.at.x - cam[0], target.at.y - cam[1]
            core.add_glow(surf, (x, y), 70, core.TEAL, 0.35 + 0.15 * math.sin(self.t * 4))
            img = core.text(f"tühik · kummita: {target.data['name']}", "mono", 15, core.CREAM)
            back = core.panel((img.get_width() + 22, 28), (30, 60, 60), 220, 10)
            surf.blit(back, back.get_rect(center=(x, y - 70)))
            surf.blit(img, img.get_rect(center=(x, y - 70)))

        self.draw_checklist(surf)
        self.draw_over(surf, cam)

    def draw_checklist(self, surf):
        facts = self.facts()
        blanks = self.rec["blanks"]
        surf.blit(core.panel((330, 44 + 26 * len(blanks)), (40, 28, 26), 190, 12), (16, 14))
        core.draw_text(surf, "kirjest puudu", (30, 22), "mono", 14, core.TEAL)
        for i, (blank, f) in enumerate(zip(blanks, facts)):
            y = 44 + i * 26
            got = f["state"] != "world"
            core.draw_text(surf, blank["label"], (30, y + 3), "mono", 14, core.DIM)
            core.draw_text(surf, f["value"] if got else "?", (170, y - 2), "serif", 21, core.CREAM if got else core.WARM)
        core.draw_text(surf, "shift – sööst läbi seina   ·   esc – tagasi serverisse", (core.W - 16 - 450, 18), "mono", 13, core.CREAM, alpha=190)
