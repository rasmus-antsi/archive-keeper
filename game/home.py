"""Home: the inside of the old archive machine, where the keeper lives."""
import math
import os

import pygame

from . import core, layout
from .level import Stage

SIZE = (1900, 1200)
ROOM = pygame.Rect(140, 340, 1620, 700)
START = (900, 820)
TERMINAL = (510, 960)
HATCH = (950, 990)
SHELF = (1530, 548)           # keepsakes stand here
LIIS = "Liis, päevavahetus"

BOOT = (
    ("Hoidja, kas sa oled ärkvel? Siin Liis, päevavahetusest.", LIIS),
    ("Vana arhiivimasin lülitatakse hommikul välja. Kõik kirjed kolivad uude muuseumisse.", LIIS),
    ("Aga üks sahtel ei taha kopeeruda: kirje on poolik. Sina elad seal sees. Kas vaatad järele, mis sealt puudu on?", LIIS),
    ("Liigu nooltega või hoia hiirt all. Shift teeb sööstu. Vilkuv sahtel on ülal seinas.", ""),
)


def trip_ready(rec):
    return "trip" in rec and os.path.exists(f"data/levels/{rec['trip']}.json")


class Home(Stage):
    def __init__(self, game, arrive=None, control=True):
        super().__init__(game, "maps/home.png", SIZE, game.home_pos or START, control)
        self.arrive, self.arrive_t = arrive, 0.0
        self.drawers = []
        n = len(game.records)
        for i, rec in enumerate(game.records):
            x = ROOM.x + 110 + i * (ROOM.w - 220) / (n - 1)
            self.drawers.append(core.Hotspot((x, ROOM.y + 64), 60, rec, repeat=True, linger=0.7))
        self.terminal = core.Hotspot(TERMINAL, 86, repeat=True, linger=0.6)
        self.hatch = core.Hotspot(HATCH, 80, repeat=True, linger=1.2)
        self.keepsakes = [core.image(f"obj/keepsake_{rid}.png", scale=1) for rid in game.restored]
        if arrive:
            core.play("unlock.ogg", 0.8)
            self.say(f"See kopeerus! „{game.by_id[arrive]['title']}“ on nüüd terve. Ma ei tea, kuidas sa seda teed.", LIIS)
            if self.all_done():
                self.say("See oli viimane. Väljas hakkab valgeks minema. Põrandaluuk on lahti: tule vaata, kuhu su kirjed kolisid.", LIIS)
        elif control and not game.seen_intro:
            game.seen_intro = True
            for text, who in BOOT:
                self.say(text, who)

    def walkable(self, p):
        return ROOM.collidepoint(p)

    def complete(self, rec):
        return "trip" not in rec or rec["id"] in self.game.restored

    def all_done(self):
        return all(self.complete(r) for r in self.game.records if trip_ready(r))

    def update(self, dt, events):
        self.step(dt)
        game = self.game
        game.home_pos = pygame.Vector2(self.ghost.pos)
        if self.arrive:
            self.arrive_t += dt
        if not self.control:
            return
        for hs in self.drawers:
            if hs.update(dt, self.ghost.pos):
                rec = hs.data
                if self.complete(rec):
                    self.say_now(rec["caption"], f"{rec['title']} · {rec['where']}")
                else:
                    core.play("enter.ogg", 0.6)
                    game.home_pos = hs.pos + pygame.Vector2(0, 90)
                    from .card import Card
                    game.go(lambda rec=rec: Card(game, rec))
        if self.terminal.update(dt, self.ghost.pos):
            self.say_now(self.note(), LIIS)
        if self.all_done() and self.hatch.update(dt, self.ghost.pos):
            core.play("restore.ogg", 0.7)
            from .world import World
            game.go(lambda: World(game, epilogue=True))

    def note(self):
        if self.all_done():
            return "Kõik on kopeeritud. Põrandaluuk on lahti. Tule, ma näitan sulle uut maja."
        left = [r for r in self.game.records if trip_ready(r) and not self.complete(r)]
        return (f"Poolikuid kirjeid on veel {len(left)}. Vilkuv sahtel on ülal seinas. "
                "Astu kirje sisse, vaata oma silmaga järele ja tule tagasi.")

    def draw(self, surf):
        game = self.game
        cam = self.draw_map(surf)
        for hs in self.drawers:
            rec = hs.data
            x, y = hs.pos.x - cam[0], ROOM.y - 26 - cam[1]
            plate = pygame.Rect(0, 0, 46, 30)
            plate.center = (x, y)
            if self.complete(rec):
                k = core.ease(self.arrive_t / 1.5) if rec["id"] == self.arrive else 1.0
                core.add_glow(surf, (x, y), 60, core.WARM, 0.5 * k)
                pygame.draw.rect(surf, (250, 226, 170), plate, border_radius=5)
                pygame.draw.rect(surf, (150, 104, 64), plate, 3, border_radius=5)
            elif trip_ready(rec):
                img = core.image(f"static_{int(self.t * 7) % 4}.png", scale=0.45)
                core.add_glow(surf, (x, y), 80, core.TEAL, 0.5 + 0.3 * math.sin(self.t * 5))
                surf.blit(img, img.get_rect(center=(x, y - 6)), special_flags=pygame.BLEND_RGB_ADD)
                hs.draw(surf, core.TEAL, cam)
            else:
                pygame.draw.rect(surf, (96, 80, 76), plate, border_radius=5)
            if hs.inside:
                name = rec["title"] if self.complete(rec) else f"poolik kirje · {rec['where']}"
                img = core.text(name, "mono", 15, core.CREAM)
                back = core.panel((img.get_width() + 20, 26), (40, 28, 26), 210, 8)
                at = (hs.pos.x - cam[0], hs.pos.y + 50 - cam[1])
                surf.blit(back, back.get_rect(center=at))
                surf.blit(img, img.get_rect(center=at))
        self.terminal.draw(surf, (120, 240, 190), cam)
        for i, img in enumerate(self.keepsakes):
            surf.blit(img, img.get_rect(midbottom=(SHELF[0] + i * 70 - cam[0], SHELF[1] + 14 - cam[1])))
        if self.all_done() and self.control:
            hx, hy = HATCH[0] - cam[0], HATCH[1] - cam[1]
            core.add_glow(surf, (hx, hy), 170, (255, 226, 170), 0.5 + 0.2 * math.sin(self.t * 2))
            pygame.draw.ellipse(surf, (255, 240, 200), (hx - 60, hy - 26, 120, 52), 4)
            self.hatch.draw(surf, core.WARM, cam)
        self.ghost.draw(surf, cam)
        self.draw_over(surf, cam)


class Title:
    """The title sits over the live machine room."""

    def __init__(self, game):
        self.game = game
        self.t = 0.0
        self.home = Home(game, control=False)
        self.veil = pygame.Surface((core.W, core.H))
        self.veil.fill((30, 18, 20))
        self.veil.set_alpha(130)

    def update(self, dt, events):
        self.t += dt
        self.home.update(dt, [])
        if self.t > 0.5 and (core.pressed_confirm(events) or core.clicked(events)):
            self.game.go(lambda: Home(self.game))

    def draw(self, surf):
        self.home.draw(surf)
        surf.blit(self.veil, (0, 0))
        core.draw_text(surf, "ARHIIVIHOIDJA", (core.W / 2, 190), "bold", 96, core.CREAM, center=True)
        core.draw_text(surf, "vaim vanas arhiivimasinas", (core.W / 2, 266), "italic", 34, core.WARM, center=True)
        a = int(160 + 90 * math.sin(self.t * 2.4))
        core.draw_text(surf, "vajuta tühikut", (core.W / 2, 600), "mono", 22, core.CREAM, center=True, alpha=a)
        core.draw_text(surf, "M – muusika sisse/välja", (core.W / 2, 690), "mono", 14, core.DIM, center=True)
