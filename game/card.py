"""The record card: decide which remembered pieces belong here, then watch it come back."""
import math

import pygame

from . import core

CARD = pygame.Rect(74, 14, 1132, 640)
BOX = pygame.Rect(CARD.x + 610, CARD.y + 120, 470, 352)   # the artefact image
FIELD_X = CARD.x + 48
VALUE_X = CARD.x + 230
FIELD_Y = CARD.y + 140
ROW = 44
RED = (160, 66, 52)
SOFT = (130, 112, 96)


class Card:
    def __init__(self, game, rec):
        self.game = game
        self.rec = rec
        self.t = 0.0
        self.paper = core.image("card.png")
        self.given = rec["given"]
        self.blanks = rec["blanks"]
        self.mine = [f for f in game.fragments if f["rid"] == rec["id"]]
        self.active = self.next_open()
        self.cursor = 0
        self.shake = {}                        # id(fragment) -> time left
        self.fly = None                        # [fragment, from, to, t]
        self.hint = 0.0
        self.reveal = None                     # seconds since the card was completed
        full = core.image(rec["image"], scale=1)
        k = min(BOX.w / full.get_width(), BOX.h / full.get_height())
        self.full = pygame.transform.smoothscale(full, (round(full.get_width() * k), round(full.get_height() * k)))
        self.pix_n = None
        self.pix = None
        self.stamp = None

    # ---------------------------------------------------------------- state

    def placed(self, idx):
        return any(f["idx"] == idx and f["state"] == "placed" for f in self.mine)

    def open_blanks(self):
        return [i for i in range(len(self.blanks)) if not self.placed(i)]

    def next_open(self):
        left = self.open_blanks()
        return left[0] if left else None

    def chips(self):
        """What the keeper carries from this wing, laid out in rows along the card's bottom."""
        held = self.game.held(self.rec["wing"])
        rows, row, width = [], [], 0
        for f in held:
            w = core.text(f["value"], "bold", 21, core.CREAM).get_width() + 30
            if row and width + w > CARD.w - 110:
                rows.append((row, width))
                row, width = [], 0
            row.append((f, w))
            width += w + 10
        if row:
            rows.append((row, width))
        out = []
        y = CARD.bottom - 20 - len(rows) * 46
        for row, width in rows:
            x = CARD.centerx - (width - 10) / 2
            for f, w in row:
                out.append((f, pygame.Rect(x, y, w, 40)))
                x += w + 10
            y += 46
        return out

    def field_rect(self, idx):
        return pygame.Rect(VALUE_X - 8, FIELD_Y + (len(self.given) + idx) * ROW - 4, 360, ROW - 6)

    def leave(self):
        from .home import Home
        self.game.go(lambda: Home(self.game))

    def enter(self):
        from .level import Level
        core.play("enter.ogg", 0.7)
        self.game.go(lambda: Level(self.game, self.rec["trip"]))

    # ---------------------------------------------------------------- logic

    def choose(self, frag, rect):
        if self.fly or self.active is None:
            return
        if frag["rid"] == self.rec["id"] and frag["idx"] == self.active:
            core.play("place.ogg", 0.7)
            self.fly = [frag, pygame.Vector2(rect.topleft), pygame.Vector2(self.field_rect(frag["idx"]).topleft), 0.0]
        else:
            core.play("wrong.ogg", 0.6)
            self.shake[id(frag)] = 0.35
            self.hint = 2.2

    def update(self, dt, events):
        self.t += dt
        self.hint = max(0.0, self.hint - dt)
        for key in list(self.shake):
            self.shake[key] -= dt
            if self.shake[key] <= 0:
                del self.shake[key]

        if self.reveal is not None:
            self.reveal += dt
            if self.reveal > 3.2 and (core.pressed_confirm(events) or core.clicked(events)):
                self.game.restored.append(self.rec["id"])
                from .home import Home
                self.game.go(lambda: Home(self.game, arrive=self.rec["id"]))
            return

        if self.fly:
            self.fly[3] += dt / 0.4
            if self.fly[3] >= 1:
                self.fly[0]["state"] = "placed"
                self.fly = None
                self.active = self.next_open()
                self.cursor = 0
                if self.active is None:
                    self.reveal = 0.0
                    core.play("restore.ogg", 0.8)
            return

        if core.pressed(events, pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.leave()
            return
        chips = self.chips()
        if not chips:
            if core.pressed_confirm(events) or core.clicked(events):
                self.enter()
            return
        open_idx = self.open_blanks()
        if core.pressed(events, pygame.K_RIGHT, pygame.K_d):
            self.cursor += 1
        if core.pressed(events, pygame.K_LEFT, pygame.K_a):
            self.cursor -= 1
        self.cursor %= len(chips)
        step = core.pressed(events, pygame.K_DOWN, pygame.K_s) - core.pressed(events, pygame.K_UP, pygame.K_w)
        if step:
            self.active = open_idx[(open_idx.index(self.active) + step) % len(open_idx)]
        if core.pressed_confirm(events):
            self.choose(*chips[self.cursor])
        click = core.clicked(events)
        if click:
            for i, (frag, rect) in enumerate(chips):
                if rect.collidepoint(click):
                    self.cursor = i
                    self.choose(frag, rect)
            for idx in open_idx:
                if self.field_rect(idx).collidepoint(click):
                    self.active = idx
        else:
            mouse = pygame.mouse.get_pos()
            if pygame.mouse.get_rel() != (0, 0):
                for i, (_, rect) in enumerate(chips):
                    if rect.collidepoint(mouse):
                        self.cursor = i

    # ---------------------------------------------------------------- drawing

    def draw_image(self, surf):
        pygame.draw.rect(surf, (212, 198, 168), BOX)
        rect = self.full.get_rect(center=BOX.center)
        if self.reveal is None:
            img = core.image(f"static_{int(self.t * 7) % 4}.png", scale=1)
            surf.blit(pygame.transform.scale(img, BOX.size), BOX)
            core.draw_text(surf, "?", BOX.center, "bold", 120, core.CREAM, center=True, alpha=170)
        else:
            # the picture resolves from a few blocks into the real thing
            k = core.ease(self.reveal / 2.4) ** 2
            n = int(5 + (rect.w - 5) * k)
            if n >= rect.w:
                surf.blit(self.full, rect)
            else:
                if n != self.pix_n:
                    small = pygame.transform.smoothscale(self.full, (n, max(1, n * rect.h // rect.w)))
                    self.pix, self.pix_n = pygame.transform.scale(small, rect.size), n
                surf.blit(self.pix, rect)
        pygame.draw.rect(surf, core.INK, BOX, 2)

    def draw_stamp(self, surf):
        k = (self.reveal - 2.4) / 0.25
        if k <= 0:
            return
        if self.stamp is None:
            label = core.text("TAASTATUD", "mono", 44, RED)
            base = pygame.Surface((label.get_width() + 40, label.get_height() + 22), pygame.SRCALPHA)
            pygame.draw.rect(base, RED, base.get_rect(), 5, border_radius=8)
            base.blit(label, (20, 12))
            self.stamp = pygame.transform.rotozoom(base, 11, 1.0)
        img = self.stamp
        if k < 1:
            img = pygame.transform.rotozoom(img, 0, 1 + (1 - k) * 0.8)
            img.set_alpha(int(255 * k))
        surf.blit(img, img.get_rect(center=(FIELD_X + 250, CARD.bottom - 150)))

    def draw(self, surf):
        surf.fill((44, 30, 28))
        core.add_glow(surf, CARD.center, 620, (70, 50, 30))
        surf.blit(self.paper, CARD)
        rec = self.rec
        core.draw_text(surf, rec["kind"].upper(), (FIELD_X, CARD.y + 34), "mono", 18, RED)
        number = core.text(rec["number"], "mono", 18, SOFT)
        surf.blit(number, (CARD.right - 48 - number.get_width(), CARD.y + 34))
        core.draw_text(surf, rec["title"], (FIELD_X, CARD.y + 58), "bold", 42, core.INK)

        for i, (label, value) in enumerate(self.given):
            y = FIELD_Y + i * ROW
            core.draw_text(surf, label, (FIELD_X, y + 8), "mono", 16, SOFT)
            core.draw_text(surf, value, (VALUE_X, y), "serif", 26, core.INK)
        for idx, blank in enumerate(self.blanks):
            y = FIELD_Y + (len(self.given) + idx) * ROW
            core.draw_text(surf, blank["label"], (FIELD_X, y + 8), "mono", 16, SOFT)
            if self.placed(idx):
                core.draw_text(surf, blank["value"], (VALUE_X, y), "bold", 26, core.INK)
            else:
                rect = self.field_rect(idx)
                if idx == self.active and self.reveal is None:
                    glow = pygame.Surface(rect.size, pygame.SRCALPHA)
                    glow.fill((230, 170, 80, int(70 + 40 * math.sin(self.t * 4))))
                    surf.blit(glow, rect)
                for x in range(rect.x + 6, rect.right - 10, 14):
                    pygame.draw.line(surf, SOFT, (x, rect.bottom - 6), (x + 7, rect.bottom - 6), 2)

        self.draw_image(surf)

        if self.reveal is not None:
            self.draw_stamp(surf)
            a = int(255 * core.ease((self.reveal - 1.4) / 1.0))
            if a > 0:
                y = BOX.bottom + 14
                for line in core.wrap(rec["caption"], "italic", 21, BOX.w):
                    core.draw_text(surf, line, (BOX.x, y), "italic", 21, core.INK, alpha=a)
                    y += 26
                core.draw_text(surf, f"Allikas: {rec['source']['name']}", (FIELD_X, CARD.bottom - 66), "mono", 15, SOFT, alpha=a)
                core.draw_text(surf, rec["source"]["ref"], (FIELD_X, CARD.bottom - 44), "mono", 15, SOFT, alpha=a)
            if self.reveal > 3.2:
                core.draw_text(surf, "tühik – pane see välja", (core.W / 2, core.H - 30), "mono", 18, core.CREAM, center=True,
                               alpha=int(170 + 80 * math.sin(self.t * 3)))
            return

        chips = self.chips()
        if not chips:
            core.draw_text(surf, "See kirje on poolik. Paberist enam ei piisa.", (CARD.centerx, CARD.bottom - 96), "italic", 24, SOFT, center=True)
            core.draw_text(surf, "Astu sisse ja vaata oma silmaga järele.", (CARD.centerx, CARD.bottom - 64), "italic", 24, SOFT, center=True)
            core.draw_text(surf, "tühik – astu kirje sisse   ·   esc – tagasi", (core.W / 2, core.H - 30), "mono", 18, core.CREAM, center=True,
                           alpha=int(190 + 60 * math.sin(self.t * 3)))
            return
        for i, (frag, rect) in enumerate(chips):
            if self.fly and frag is self.fly[0]:
                continue
            r = rect.move(math.sin(self.t * 60) * 5 if id(frag) in self.shake else 0, 0)
            pygame.draw.rect(surf, (70, 60, 76) if i != self.cursor else (96, 64, 50), r, border_radius=11)
            if i == self.cursor:
                pygame.draw.rect(surf, (230, 170, 80), r.inflate(6, 6), 3, border_radius=13)
            core.draw_text(surf, frag["value"], r.center, "bold", 21, core.CREAM, center=True)
        if self.fly:
            frag, a, b, k = self.fly
            core.draw_text(surf, frag["value"], a.lerp(b, core.ease(k)), "bold", 26, core.INK)
        # the memory behind the selected piece, so matching is reading, not guessing
        if self.hint:
            core.draw_text(surf, "See käib mujale.", (core.W / 2, core.H - 44), "italic", 23, (240, 150, 130), center=True)
        elif chips:
            line = chips[min(self.cursor, len(chips) - 1)][0]["line"]
            rows = core.wrap(line, "italic", 21, core.W - 120)
            for j, row in enumerate(rows[:2]):
                core.draw_text(surf, row, (core.W / 2, core.H - 50 + j * 24), "italic", 21, core.CREAM, center=True)
        core.draw_text(surf, "esc – tagasi", (CARD.x, 2), "mono", 12, core.DIM)
