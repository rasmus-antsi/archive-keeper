"""The museum, seen from above: wander, gather memories, restore exhibits, open the doors."""
import math
import random

import pygame

from . import core, layout
from .ghost import Ghost

SIGNED = "Liis, päevavahetus"
INTRO = ("Tere, Hoidja! Uus muuseum on valmis, aga alused on tühjad: sildita asju me välja panna ei saa. "
         "Vanast süsteemist tulid kirjed üle poolikult. Sina mäletad, mis kuhu käis. Alusta Linnasaalist, vasakul.")
OUTRO = (
    (1.0, "Hommik. Uksed on lahti."),
    (7.0, "Inimesed seisavad asjade ees, mida eile veel ei olnud."),
    (13.5, "Vana süsteem lülitatakse nüüd välja. Aga kõik, mida sa mäletasid, on nüüd nende oma."),
)
CREDITS_AT = 20.0


def progress_note(game):
    n, total = len(game.restored), len(game.records)
    if n == 0:
        return INTRO
    locked = [d for w, d in layout.WINGS.items() if w not in game.unlocked]
    if locked:
        nxt = min(locked, key=lambda d: d["unlock"])
        return f"{n} kirjet on väljas. {nxt['name']} avaneb, kui taastatud on {nxt['unlock']}. Kiiret ei ole."
    if n < layout.OPEN_AT:
        return f"{n} kirjet on väljas ja kõik saalid lahti. Kui taastatud on {layout.OPEN_AT}, võime uksed avada."
    if n < total:
        return (f"{n} kirjet {total}-st. Välisukse võib juba avada, see on fuajee allservas. "
                "Aga võid ka enne kõik lõpuni teha, mina ootan.")
    return "Kõik kirjed on väljas. Uks on sinu avada. Aitäh, et mäletasid."


class Visitor:
    def __init__(self, room, pos=None, image=None):
        self.room = pygame.Rect(room).inflate(-120, -160)
        self.img = image or core.image(f"visitor_{random.randrange(5)}.png", scale=1)
        self.pos = pygame.Vector2(pos or self.pick())
        self.target = self.pick()
        self.wait = random.uniform(0, 3)
        self.phase = random.uniform(0, 6)

    def pick(self):
        return pygame.Vector2(random.uniform(self.room.left, self.room.right), random.uniform(self.room.top, self.room.bottom))

    def update(self, dt):
        if self.wait > 0:
            self.wait -= dt
            return
        to = self.target - self.pos
        if to.length() < 6:
            self.target = self.pick()
            self.wait = random.uniform(2, 6)
        else:
            self.pos += to.normalize() * 46 * dt
            self.phase += dt * 9

    def draw(self, surf, cam):
        bob = abs(math.sin(self.phase)) * 3 if self.wait <= 0 else 0
        surf.blit(self.img, self.img.get_rect(midbottom=(self.pos.x - cam[0], self.pos.y - cam[1] - bob)))


class World:
    def __init__(self, game, arrive=None, control=True, epilogue=False):
        self.game = game
        if epilogue:
            # everything the keeper remembered has moved into the new museum
            game.restored = [r["id"] for r in game.records]
            game.unlocked = set(layout.WINGS)
            game.pos = pygame.Vector2(layout.START)
            game.seen_intro = True
        self.t = 0.0
        self.control = control
        self.map = core.image("map.png", scale=1).convert()
        self.rooms = {k: pygame.Rect(v) for k, v in layout.ROOMS.items()}
        self.doors = {k: pygame.Rect(d["door"]) for k, d in layout.WINGS.items()}
        self.ghost = Ghost(game.pos)
        self.cam = self.cam_target()
        self.motes = core.Motes(12, (255, 226, 180))
        self.box = core.TextBox()
        self.floaters = []
        self.toast = None                  # [title, sub, age]
        self.room = self.room_at(self.ghost.pos)
        self.ending = None                 # seconds since the doors opened
        self.sheet = None

        self.wisps = []
        for f in game.fragments:
            if f["state"] == "world":
                hs = core.Hotspot(f["pos"], 62, f, linger=0.7)
                self.wisps.append(hs)
        self.plinths = []
        slots = {w: iter(p) for w, p in layout.PLINTHS.items()}
        for rec in game.records:
            x, y = next(slots[rec["wing"]])
            self.plinths.append(core.Hotspot((x, y + 70), 74, rec, repeat=True, linger=0.8))
        self.board = core.Hotspot(layout.BOARD, 84, repeat=True, linger=0.6)
        self.entrance = core.Hotspot(layout.ENTRANCE, 84, repeat=True, linger=1.2)
        self.thumbs = {}
        self.veils = {}
        for wing, room in self.rooms.items():
            if wing in layout.WINGS:
                veil = pygame.Surface((room.w + 80, room.h + 150))
                veil.fill((34, 20, 22))
                self.veils[wing] = veil
        self.visitors = []
        for wing in layout.WINGS:
            for _ in range(game.restored_in(wing)):
                self.visitors.append(Visitor(self.rooms[wing]))
        self.arrive, self.arrive_t = arrive, 0.0

        if arrive:
            core.play("chime_4.ogg", 0.6)
            opened = [w for w, d in layout.WINGS.items() if w not in game.unlocked and len(game.restored) >= d["unlock"]]
            for w in opened:
                game.unlocked.add(w)
            if opened:
                core.play("unlock.ogg", 0.8)
                d = layout.WINGS[opened[0]]
                self.box.say(f"{d['name']} on nüüd lahti! Seal ootavad uued kirjed: {d['sub']}.", SIGNED, hold=9)
            elif len(game.restored) in (layout.OPEN_AT, len(game.records)):
                self.box.say(progress_note(game), SIGNED, hold=10)
        elif epilogue:
            self.box.say("Uus muuseum. Kõik, mida sa mäletasid, seisab nüüd siin oma koha peal. "
                         "Käi ringi. Kui oled valmis, ava fuajee allservas välisuks.", SIGNED, hold=14)
        elif control and not game.seen_intro:
            game.seen_intro = True
            self.box.say("Liigu nooltega või hoia hiirt all. Peatu helendava täpi juures, et seda mäletada. "
                         "Ülal seinal on sulle teade.", hold=11)

    # ---------------------------------------------------------------- space

    def walkable(self, p):
        if self.rooms["fuajee"].collidepoint(p):
            return True
        return any(self.rooms[w].collidepoint(p) or self.doors[w].collidepoint(p) for w in self.game.unlocked)

    def room_at(self, p):
        for name, rect in self.rooms.items():
            if rect.collidepoint(p):
                return name
        return None

    def cam_target(self):
        x = max(0, min(layout.WORLD[0] - core.W, self.ghost.pos.x - core.W / 2))
        y = max(0, min(layout.WORLD[1] - core.H, self.ghost.pos.y - 30 - core.H / 2))
        return pygame.Vector2(x, y)

    def thumb(self, rec):
        if rec["id"] not in self.thumbs:
            img = core.image(rec["image"], scale=1)
            k = min(92 / img.get_width(), 78 / img.get_height())
            small = pygame.transform.smoothscale(img, (round(img.get_width() * k), round(img.get_height() * k)))
            frame = pygame.Surface((small.get_width() + 14, small.get_height() + 14), pygame.SRCALPHA)
            pygame.draw.rect(frame, (112, 76, 48), frame.get_rect(), border_radius=5)
            frame.blit(small, (7, 7))
            self.thumbs[rec["id"]] = frame
        return self.thumbs[rec["id"]]

    # ---------------------------------------------------------------- update

    def update(self, dt, events):
        game = self.game
        self.t += dt
        mouse_world = pygame.Vector2(pygame.mouse.get_pos()) + self.cam
        self.ghost.update(dt, self.control, mouse_world, self.walkable)
        game.pos = pygame.Vector2(self.ghost.pos)
        self.cam += (self.cam_target() - self.cam) * min(1.0, 5 * dt)
        self.motes.update(dt)
        self.box.update(dt)
        for v in self.visitors:
            v.update(dt)
        for f in self.floaters:
            f[2] += dt
        self.floaters = [f for f in self.floaters if f[2] < 1.6]
        if self.arrive:
            self.arrive_t += dt
        if self.toast:
            self.toast[2] += dt
            if self.toast[2] > 3.5:
                self.toast = None
        room = self.room_at(self.ghost.pos)
        if room and room != self.room:
            self.room = room
            if room in layout.WINGS:
                d = layout.WINGS[room]
                self.toast = [d["name"], f"{d['sub']} · {game.restored_in(room)}/4 taastatud", 0.0]
            else:
                self.toast = ["Fuajee", "", 0.0]

        if self.ending is not None:
            self.update_ending(dt, events)
            return
        if not self.control:
            return

        for hs in self.wisps:
            if hs.update(dt, self.ghost.pos):
                f = hs.data
                f["state"] = "held"
                core.play(f"chime_{random.randrange(6)}.ogg", 0.5)
                self.box.say(f["line"], hold=8)
                self.floaters.append([f["value"], pygame.Vector2(hs.pos), 0.0])
        self.wisps = [hs for hs in self.wisps if not hs.done]

        for hs in self.plinths:
            if hs.update(dt, self.ghost.pos):
                rec = hs.data
                self.box.say(rec["caption"], f"{rec['title']} · {rec['where']}", hold=10)
        if self.board.update(dt, self.ghost.pos):
            self.box.say(progress_note(game), SIGNED, hold=13)
        if self.entrance.update(dt, self.ghost.pos):
            if len(game.restored) >= layout.OPEN_AT:
                self.open_doors()
            else:
                self.box.say(f"Uks on veel kinni. Avada saab siis, kui taastatud on {layout.OPEN_AT} kirjet.", hold=5)

    def open_doors(self):
        core.play("restore.ogg", 0.7)
        self.ending = 0.0
        self.said = 0
        ex, ey = layout.ENTRANCE
        halls = list(self.rooms.values())
        for i in range(10):
            v = Visitor(halls[i % len(halls)], pos=(ex + random.uniform(-40, 40), ey + 20 + i * 4))
            v.wait = 1.0 + i * 0.9
            self.visitors.append(v)

    def update_ending(self, dt, events):
        self.ending += dt
        if self.said < len(OUTRO) and self.ending > OUTRO[self.said][0]:
            self.box.say(OUTRO[self.said][1], hold=5.5)
            self.said += 1
        if self.ending > CREDITS_AT + 2 and core.pressed_confirm(events):
            self.game.restart()

    # ---------------------------------------------------------------- draw

    def credits(self):
        if self.sheet is None:
            game = self.game
            sheet = core.panel((940, 600), (40, 28, 26), 238)
            n = len(game.restored)
            head = "Kõik kirjed on päris." if n == len(game.records) else f"{n} kirjet {len(game.records)}-st on väljas. Kõik on päris."
            y = core.draw_text(sheet, head, (470, 52), "bold", 38, core.CREAM, center=True).bottom + 22
            groups = {}
            for rec in game.records:
                groups.setdefault((rec["source"]["name"], rec["source"]["url"].split("/object")[0]), []).append(rec["number"])
            for (name, url), numbers in groups.items():
                core.draw_text(sheet, name, (60, y), "bold", 24, core.WARM)
                refs = "; ".join(numbers)
                y = core.draw_wrapped(sheet, refs, (60, y + 32), 820, "mono", 15, core.CREAM, line_gap=3)
                core.draw_text(sheet, url, (60, y + 2), "mono", 15, core.DIM)
                y += 40
            y = core.draw_wrapped(sheet, "Vallakohtute protokolle on arhiivis säilinud umbes 600 000. Vabatahtlikud on neist "
                                  "käsitsi sisse trükkinud üle 100 000. Ülejäänud ootavad oma silti.",
                                  (60, y + 4), 820, "serif", 23, core.CREAM)
            core.draw_text(sheet, "ra.ee/vallakohtud  ·  ajapaik.ee  ·  muis.ee", (470, y + 24), "mono", 18, core.TEAL, center=True)
            core.draw_text(sheet, "Kaartidel olev on arhiivist. Jutuajamised ja kummitamine on mängu väljamõeldis.",
                           (470, y + 56), "italic", 19, core.CREAM, center=True)
            core.draw_text(sheet, "tühik – algusesse", (470, 572), "mono", 15, core.DIM, center=True)
            self.sheet = sheet
        return self.sheet

    def draw(self, surf):
        game = self.game
        cam = (round(self.cam.x), round(self.cam.y))
        surf.blit(self.map, (0, 0), pygame.Rect(cam, (core.W, core.H)))

        # exhibits on their plinths
        for hs in self.plinths:
            rec = hs.data
            x, y = hs.pos.x - cam[0], hs.pos.y - 70 - cam[1]
            if not -120 < x < core.W + 120 or not -160 < y < core.H + 160:
                continue
            if rec["id"] in game.restored:
                k = core.ease(self.arrive_t / 1.8) if rec["id"] == self.arrive else 1.0
                core.add_glow(surf, (x, y + 10), 120, core.WARM, 0.45 * k)
                img = self.thumb(rec)
                if k < 1:
                    img = img.copy()
                    img.set_alpha(int(255 * k))
                surf.blit(img, img.get_rect(midbottom=(x, y + 44 + (1 - k) * 14)))
            else:
                img = core.image(f"static_{int(self.t * 7 + hs.pos.x) % 4}.png", scale=0.6)
                surf.blit(img, img.get_rect(midbottom=(x, y + 44)), special_flags=pygame.BLEND_RGB_ADD)

        # wings that are not finished stay dim; locked ones are dark
        dawn = core.ease(self.ending / 4) if self.ending is not None else 0.0
        for wing, veil in self.veils.items():
            room = self.rooms[wing]
            if wing in game.unlocked:
                alpha = 70 * (1 - game.restored_in(wing) / 4)
            else:
                alpha = 214
            alpha = int(alpha * (1 - dawn))
            if alpha > 2:
                veil.set_alpha(alpha)
                surf.blit(veil, (room.x - 40 - cam[0], room.y - 110 - cam[1]))
            if wing not in game.unlocked:
                d = layout.WINGS[wing]
                door = self.doors[wing]
                pos = (door.centerx - cam[0], door.centery - cam[1])
                core.add_glow(surf, pos, 90, core.TEAL, 0.25)
                core.draw_text(surf, d["name"], (pos[0], pos[1] - 14), "bold", 22, core.CREAM, center=True)
                core.draw_text(surf, f"avaneb: {len(game.restored)}/{d['unlock']}", (pos[0], pos[1] + 12), "mono", 14, core.TEAL, center=True)

        for hs in self.wisps:
            if hs.data["wing"] in game.unlocked:
                self.draw_wisp(surf, hs, cam)
        for hs in self.plinths:
            if hs.data["wing"] in game.unlocked and hs.data["id"] not in game.restored:
                hs.draw(surf, core.TEAL, cam)
            if hs.inside:
                rec = hs.data
                name = rec["title"] if rec["id"] in game.restored else f"puudulik kirje · {rec['where']}"
                img = core.text(name, "mono", 15, core.CREAM)
                back = core.panel((img.get_width() + 20, 26), alpha=190, radius=8)
                pos = (hs.pos.x - cam[0], hs.pos.y - 150 - cam[1])
                surf.blit(back, back.get_rect(center=pos))
                surf.blit(img, img.get_rect(center=pos))
        self.board.draw(surf, core.WARM, cam)
        can_open = len(game.restored) >= layout.OPEN_AT and self.ending is None
        self.entrance.draw(surf, core.WARM if can_open else core.DIM, cam)
        if can_open:
            ex, ey = layout.ENTRANCE
            core.add_glow(surf, (ex - cam[0], ey + 30 - cam[1]), 130, core.WARM, 0.4 + 0.15 * math.sin(self.t * 2))
        if dawn:
            ex, ey = layout.ENTRANCE
            core.add_glow(surf, (ex - cam[0], ey + 40 - cam[1]), 320, (255, 226, 170), 0.6 * dawn)

        things = [(v.pos.y, v) for v in self.visitors] + [(self.ghost.pos.y + 30, self.ghost)]
        for _, thing in sorted(things, key=lambda t: t[0]):
            thing.draw(surf, cam)
        self.motes.draw(surf)

        for value, pos, age in self.floaters:
            k = core.ease(age / 1.2)
            img = core.text(f"+ {value}", "bold", 24, core.CREAM)
            back = core.panel((img.get_width() + 24, img.get_height() + 10), alpha=int(200 * (1 - max(0, age - 1.1) / 0.5)))
            at = (pos.x - cam[0], pos.y - 50 - 50 * k - cam[1])
            surf.blit(back, back.get_rect(center=at))
            surf.blit(img, img.get_rect(center=at))

        if self.control and self.ending is None:
            self.draw_hud(surf)
        if self.toast:
            title, sub, age = self.toast
            a = int(255 * min(1, age / 0.4, (3.5 - age) / 0.6))
            core.draw_text(surf, title, (core.W / 2, 92), "bold", 44, core.CREAM, center=True, alpha=a)
            if sub:
                core.draw_text(surf, sub, (core.W / 2, 132), "italic", 22, core.CREAM, center=True, alpha=a)
        self.box.draw(surf)
        if self.ending is not None:
            c = core.ease((self.ending - CREDITS_AT) / 1.5)
            if c > 0:
                sheet = self.credits()
                if c < 1:
                    sheet = sheet.copy()
                    sheet.set_alpha(int(255 * c))
                surf.blit(sheet, sheet.get_rect(center=(core.W / 2, core.H / 2)))

    def draw_wisp(self, surf, hs, cam):
        """A memory: a small bright scrap turning slowly in its own light."""
        x = hs.pos.x - cam[0]
        y = hs.pos.y - cam[1] - 16 + math.sin(hs.phase * 1.8) * 6
        if not -60 < x < core.W + 60 or not -60 < y < core.H + 60:
            return
        pulse = 0.5 + 0.5 * math.sin(hs.phase * 2.6)
        core.add_glow(surf, (x, y), 44 + 26 * hs.fill, (255, 214, 140), 0.6 + 0.25 * pulse)
        w = 9 * abs(math.cos(hs.phase * 1.4)) + 3
        pygame.draw.polygon(surf, (255, 248, 226), [(x, y - 13), (x + w, y), (x, y + 13), (x - w, y)])
        pygame.draw.polygon(surf, (236, 190, 110), [(x, y - 13), (x + w, y), (x, y + 13), (x - w, y)], 2)
        if hs.fill > 0:
            rect = pygame.Rect(0, 0, 56, 56)
            rect.center = (x, y)
            pygame.draw.arc(surf, core.CREAM, rect, math.pi / 2 - hs.fill * math.tau, math.pi / 2, 4)

    def draw_hud(self, surf):
        game = self.game
        n, total = len(game.restored), len(game.records)
        surf.blit(core.panel((250, 74), alpha=170, radius=12), (16, 14))
        core.draw_text(surf, f"taastatud {n}/{total}", (32, 24), "mono", 18, core.CREAM)
        pygame.draw.rect(surf, (70, 60, 66), (32, 52, 218, 8), border_radius=4)
        if n:
            pygame.draw.rect(surf, core.WARM, (32, 52, round(218 * n / total), 8), border_radius=4)
        locked = [d for w, d in layout.WINGS.items() if w not in game.unlocked]
        if locked:
            nxt = min(locked, key=lambda d: d["unlock"])
            goal = f"{nxt['name']} avaneb: {n}/{nxt['unlock']}"
        elif n < layout.OPEN_AT:
            goal = f"uksed avanevad: {n}/{layout.OPEN_AT}"
        else:
            goal = "välisukse võib avada"
        core.draw_text(surf, goal, (32, 66), "mono", 13, core.TEAL)

        held = game.held()
        if held:
            rows = held[-7:]
            h = 40 + 24 * len(rows)
            surf.blit(core.panel((264, h), alpha=170, radius=12), (core.W - 280, 14))
            core.draw_text(surf, f"kaasas {len(held)} mälestust", (core.W - 264, 24), "mono", 15, core.TEAL)
            for i, f in enumerate(rows):
                value = f["value"] if len(f["value"]) < 27 else f["value"][:25] + "…"
                core.draw_text(surf, value, (core.W - 264, 46 + i * 24), "serif", 20, core.CREAM)
