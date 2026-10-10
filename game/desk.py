"""Home: the archive server, seen as a file explorer the keeper lives in.

Every file is a real record. Some have blank fields; the answer is nearly
always in another file. Click a value to remember it, click a blank to
fill it from memory.
"""
import math

import pygame

from . import core

TOP = 38
SIDE = 244
CLIP_H = 52
TILE = (166, 152)
BG = (24, 26, 36)
PANEL = (32, 35, 48)
LINE = (58, 62, 80)
TEXT = (226, 224, 214)
MUTED = (140, 146, 166)
AMBER = (240, 190, 110)
TEAL = (120, 226, 210)
PAPER = (244, 236, 214)
INK = (52, 40, 34)
WIN = pygame.Rect(130, 46, 1020, 600)
LIIS = "Liis"

BOOT = (
    "Tere, Hoidja. Siin Liis, päevavahetusest. Kas sa kuuled mind seal sees?",
    "Sa oled nüüd muuseumi serveris VARAMU-02. Sa palusid ise siia jääda: ütlesid, et keegi peab neid asju mäletama.",
    "Siin on {n} päris kirjet koos piltide ja tekstidega. Homme hommikul võtab uus näitus oma sildid otse siit.",
    "Kolimisel läks osa faile katki. Mõnel on väli tühi, ühel on tekst loetamatu. Need failid vilguvad.",
    "Õige vastus on peaaegu alati kuskil olemas. Samast kogust pärit asjad tulid sama inimese käest ja samal suvel.",
    "Klõpsa väärtusel, et see meelde jätta. Klõpsa tühjal väljal, et see mälust täita. „Samast kogust“ näitab naabreid.",
    "Võid kõike lugeda, kiiret ei ole. Mina lähen nüüd koju. Hommikul näeme.",
)


def cut(string, kind, size, width):
    """Shorten a string with an ellipsis so it fits a width."""
    f = core.font(kind, size)
    if f.size(string)[0] <= width:
        return string
    while string and f.size(string + "…")[0] > width:
        string = string[:-1]
    return string + "…"


class Desk:
    def __init__(self, game, open_file=None, control=True):
        self.game = game
        self.t = 0.0
        self.control = control
        self.folder = game.desk_folder
        self.filter = None                 # (label, value) or ("group", name)
        self.scroll = 0.0
        self.open = None                   # the file in the viewer
        self.text_scroll = 0
        self.pick = None                   # label of the blank being filled
        self.shake = 0.0
        self.note = ""                     # one line of feedback inside the viewer
        self.note_t = 0.0
        self.stamp_t = None
        self.thumbs = {}
        self.ghost = core.image("ghost.png", 0.2)
        self.mouse = pygame.Vector2(pygame.mouse.get_pos())
        self.hot = []                      # (rect, action) rebuilt every frame while drawing
        self.tree = self.build_tree()
        if open_file:
            self.show(game.file_by_id[open_file])
        if control and not game.seen_intro:
            game.seen_intro = True
            for line in BOOT:
                game.liis.append(line.format(n=len(game.files)))
        pygame.mouse.set_visible(False)

    # ---------------------------------------------------------------- data

    def build_tree(self):
        counts = {}
        for f in self.game.files:
            top, sub = f["folder"].split("/")
            counts[top] = counts.get(top, 0) + 1
            counts[f["folder"]] = counts.get(f["folder"], 0) + 1
        rows = [("*", "Kõik failid", 0), ("!", "Vigased", 0), ("+", "Parandatud", 0)]
        for top in sorted(k for k in counts if "/" not in k):
            rows.append((top, top, 0))
            for sub in sorted(k for k in counts if k.startswith(top + "/")):
                rows.append((sub, sub.split("/")[1], 1))
        self.counts = counts
        return rows

    def listing(self):
        g = self.game
        if self.filter:
            label, value = self.filter
            if label == "group":
                return [f for f in g.files if f["group"] == value]
            return [f for f in g.files if any(k == label and v == value and not g.blank(f, k) for k, v in f["fields"])]
        if self.folder == "*":
            return g.files
        if self.folder == "!":
            return [f for f in g.files if g.broken(f)]
        if self.folder == "+":
            return [f for f in g.files if f["id"] in g.fixed]
        return [f for f in g.files if f["folder"] == self.folder or f["folder"].startswith(self.folder + "/")]

    def heading(self):
        if self.filter:
            label, value = self.filter
            return f"samast kogust: {value}" if label == "group" else f"{label} = {value}"
        return {"*": "Kõik failid", "!": "Vigased failid", "+": "Parandatud failid"}.get(self.folder, self.folder.replace("/", "  ›  "))

    def thumb(self, f):
        if f["id"] not in self.thumbs:
            if f.get("thumb"):
                self.thumbs[f["id"]] = core.image(f["thumb"], scale=1)
            else:
                # documents get a little sheet of paper
                s = pygame.Surface((132, 96), pygame.SRCALPHA)
                col = (150, 180, 214) if f["kind"] == "ehitusprojekt" else PAPER
                pygame.draw.rect(s, col, (34, 4, 64, 88), border_radius=4)
                for y in range(18, 84, 9):
                    pygame.draw.line(s, (120, 110, 100), (42, y), (90 - (y * 7) % 22, y), 2)
                self.thumbs[f["id"]] = s
        return self.thumbs[f["id"]]

    def show(self, f):
        self.open = f
        self.text_scroll = 0
        self.pick = None
        self.stamp_t = None
        self.note = ""

    def say_note(self, text):
        self.note, self.note_t = text, 3.0

    # ---------------------------------------------------------------- actions

    def do(self, action):
        g = self.game
        kind = action[0]
        if kind == "folder":
            self.folder = g.desk_folder = action[1]
            self.filter, self.scroll = None, 0.0
        elif kind == "open":
            self.show(action[1])
            core.play("place.ogg", 0.25)
        elif kind == "close":
            self.open = None
        elif kind == "step":
            files = self.listing()
            if self.open in files:
                self.show(files[(files.index(self.open) + action[1]) % len(files)])
        elif kind == "copy":
            g.remember(action[1], action[2])
            core.play("place.ogg", 0.5)
            self.say_note(f"Meelde jäetud: {action[2]}")
        elif kind == "find":
            self.filter, self.scroll, self.open = (action[1], action[2]), 0.0, None
        elif kind == "blank":
            if not g.clip:
                self.say_note("Mälus pole veel midagi. Otsi vastus teisest failist ja klõpsa sellel.")
            else:
                self.pick = None if self.pick == action[1] else action[1]
        elif kind == "paste":
            self.paste(action[1])
        elif kind == "forget":
            g.clip.remove(action[1])
        elif kind == "trip":
            from .level import Level
            core.play("enter.ogg", 0.7)
            pygame.mouse.set_visible(True)
            g.go(lambda: Level(g, action[1]))
        elif kind == "liis":
            g.liis.pop(0)
        elif kind == "open_show":
            from .world import World
            core.play("restore.ogg", 0.7)
            pygame.mouse.set_visible(True)
            g.go(lambda: World(g, epilogue=True))

    def paste(self, chip):
        g = self.game
        f, label = self.open, self.pick
        truth = dict(f["fields"])[label]
        if chip["value"] == truth:
            g.blanks.discard((f["id"], label))
            self.pick = None
            core.play(f"chime_{min(5, len(g.fixed) + 1)}.ogg", 0.6)
            if not g.broken(f):
                g.fixed.append(f["id"])
                self.stamp_t = 0.0
                self.note_t = 0.0
                core.play("restore.ogg", 0.7)
                g.on_fixed()
            else:
                self.say_note("Sobib. Veel on tühje välju.")
        else:
            core.play("wrong.ogg", 0.6)
            self.shake = 0.35
            self.say_note("See ei sobi siia. Loe naaberfaile veel.")

    # ---------------------------------------------------------------- update

    def update(self, dt, events):
        self.t += dt
        self.shake = max(0.0, self.shake - dt)
        self.note_t = max(0.0, self.note_t - dt)
        if self.stamp_t is not None:
            self.stamp_t += dt
        self.mouse += (pygame.Vector2(pygame.mouse.get_pos()) - self.mouse) * min(1.0, 14 * dt)
        if not self.control:
            return
        g = self.game
        for e in events:
            if e.type == pygame.MOUSEWHEEL:
                if self.open:
                    self.text_scroll = max(0, self.text_scroll - e.y)
                else:
                    self.scroll = max(0.0, self.scroll - e.y * 48)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for rect, action in reversed(self.hot):
                    if rect.collidepoint(e.pos):
                        self.do(action)
                        break
                else:
                    self.pick = None
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_RETURN) and g.liis:
                    g.liis.pop(0)
                elif e.key == pygame.K_ESCAPE:
                    if self.pick:
                        self.pick = None
                    elif self.open:
                        self.open = None
                    else:
                        self.filter = None
                elif self.open and e.key in (pygame.K_RIGHT, pygame.K_d):
                    self.do(("step", 1))
                elif self.open and e.key in (pygame.K_LEFT, pygame.K_a):
                    self.do(("step", -1))
                elif not self.open and e.key in (pygame.K_DOWN, pygame.K_s):
                    self.scroll += 152
                elif not self.open and e.key in (pygame.K_UP, pygame.K_w):
                    self.scroll = max(0.0, self.scroll - 152)

    # ---------------------------------------------------------------- draw

    def button(self, surf, rect, label, action, color=AMBER, size=15):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, color if hover else PANEL, rect, border_radius=8)
        pygame.draw.rect(surf, color, rect, 2, border_radius=8)
        core.draw_text(surf, label, rect.center, "mono", size, BG if hover else color, center=True)
        self.hot.append((rect, action))

    def draw(self, surf):
        g = self.game
        self.hot = []
        surf.fill(BG)
        self.draw_listing(surf)
        self.draw_side(surf)
        self.draw_top(surf)
        self.draw_clip(surf)
        if self.open:
            self.draw_viewer(surf)
        self.draw_liis(surf)
        # the keeper is the pointer
        mx, my = pygame.mouse.get_pos()
        gx, gy = self.mouse.x + 20, self.mouse.y + 26 + math.sin(self.t * 2.4) * 3
        core.add_glow(surf, (gx, gy), 44, (70, 120, 120), 0.7)
        surf.blit(self.ghost, self.ghost.get_rect(center=(gx, gy)))
        pygame.draw.circle(surf, TEXT, (mx, my), 4)
        pygame.draw.circle(surf, BG, (mx, my), 4, 1)

    def draw_top(self, surf):
        g = self.game
        pygame.draw.rect(surf, (18, 19, 28), (0, 0, core.W, TOP))
        pygame.draw.line(surf, LINE, (0, TOP), (core.W, TOP))
        core.draw_text(surf, "VARAMU-02", (16, 9), "mono", 17, AMBER)
        core.draw_text(surf, f"·  {len(g.files)} kirjet  ·  öövahetus", (128, 10), "mono", 15, MUTED)
        done, total = len(g.fixed), g.cases
        # the night moves toward morning as files get fixed
        minutes = 23 * 60 + int((7 * 60 + 30) * done / max(1, total))
        clock = f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"
        core.draw_text(surf, clock, (core.W - 70, 9), "mono", 17, TEXT)
        label = f"parandatud {done}/{total}"
        w = core.text(label, "mono", 15, TEAL).get_width()
        core.draw_text(surf, label, (core.W - 96 - w, 10), "mono", 15, TEAL if done < total else AMBER)

    def draw_side(self, surf):
        g = self.game
        pygame.draw.rect(surf, PANEL, (0, TOP, SIDE, core.H - TOP - CLIP_H))
        y = TOP + 12
        mouse = pygame.mouse.get_pos()
        for key, label, depth in self.tree:
            # subfolders only show under the top folder that is open
            if depth and not self.folder.startswith(key.split("/")[0]):
                continue
            rect = pygame.Rect(8, y, SIDE - 16, 25)
            if key == "!":
                count = sum(1 for f in g.files if g.broken(f))
            elif key == "+":
                count = len(g.fixed)
            elif key == "*":
                count = len(g.files)
            else:
                count = self.counts[key]
            active = self.folder == key and not self.filter
            if active:
                pygame.draw.rect(surf, (52, 56, 76), rect, border_radius=6)
            elif rect.collidepoint(mouse) and not self.open:
                pygame.draw.rect(surf, (42, 46, 62), rect, border_radius=6)
            color = TEAL if key == "!" and count else AMBER if key == "+" and count else TEXT if depth == 0 else MUTED
            if key == "!" and count:
                color = TEAL if math.sin(self.t * 5) > -0.3 else MUTED
            core.draw_text(surf, cut(label, "mono", 14, 150 - depth * 14), (18 + depth * 16, y + 5), "mono", 14, color)
            n = core.text(str(count), "mono", 12, MUTED)
            surf.blit(n, (SIDE - 20 - n.get_width(), y + 7))
            if not self.open:
                self.hot.append((rect, ("folder", key)))
            y += 26 if depth else 28
            if key == "+":
                y += 10
                pygame.draw.line(surf, LINE, (14, y - 6), (SIDE - 14, y - 6))

    def draw_listing(self, surf):
        g = self.game
        files = self.listing()
        area = pygame.Rect(SIDE, TOP, core.W - SIDE, core.H - TOP - CLIP_H)
        cols = area.w // TILE[0]
        rows = (len(files) + cols - 1) // cols
        self.scroll = max(0.0, min(self.scroll, max(0, rows * TILE[1] + 60 - area.h)))
        core.draw_text(surf, cut(self.heading(), "mono", 15, 700), (SIDE + 20, TOP + 12), "mono", 15, AMBER)
        core.draw_text(surf, f"{len(files)} faili", (core.W - 110, TOP + 13), "mono", 13, MUTED)
        if self.filter:
            rect = pygame.Rect(core.W - 290, TOP + 8, 160, 26)
            self.button(surf, rect, "x tühista filter", ("find_clear",), MUTED, 13)
            self.hot[-1] = (rect, ("folder", self.folder))
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(area.x, area.y + 40, area.w, area.h - 40))
        mouse = pygame.mouse.get_pos()
        for i, f in enumerate(files):
            x = area.x + 14 + (i % cols) * TILE[0]
            y = area.y + 48 + (i // cols) * TILE[1] - int(self.scroll)
            if y < area.y - TILE[1] or y > area.bottom:
                continue
            rect = pygame.Rect(x, y, TILE[0] - 10, TILE[1] - 8)
            broken = g.broken(f)
            hover = rect.collidepoint(mouse) and not self.open and mouse[1] > area.y + 40
            pygame.draw.rect(surf, (46, 50, 68) if hover else (34, 37, 50), rect, border_radius=8)
            img = self.thumb(f)
            surf.blit(img, img.get_rect(center=(rect.centerx, rect.y + 54)))
            if broken:
                st = core.image(f"static_{int(self.t * 7 + i) % 4}.png", scale=0.5)
                surf.blit(st, st.get_rect(center=(rect.centerx, rect.y + 54)), special_flags=pygame.BLEND_RGB_ADD)
                pygame.draw.rect(surf, TEAL if math.sin(self.t * 5 + i) > -0.3 else LINE, rect, 2, border_radius=8)
            elif f["id"] in g.fixed:
                pygame.draw.rect(surf, AMBER, rect, 2, border_radius=8)
            lines = core.wrap(f["name"], "mono", 11, rect.w - 12)[:2]
            for j, line in enumerate(lines):
                core.draw_text(surf, cut(line, "mono", 11, rect.w - 12), (rect.x + 6, rect.y + 108 + j * 14), "mono", 11, TEXT if hover else MUTED)
            if not self.open and rect.bottom > area.y + 40:
                self.hot.append((rect.clip(pygame.Rect(area.x, area.y + 40, area.w, area.h - 40)), ("open", f)))
        surf.set_clip(clip)

    def draw_clip(self, surf):
        g = self.game
        y = core.H - CLIP_H
        pygame.draw.rect(surf, (18, 19, 28), (0, y, core.W, CLIP_H))
        pygame.draw.line(surf, LINE, (0, y), (core.W, y))
        core.draw_text(surf, "MÄLU", (16, y + 17), "mono", 15, AMBER)
        x = 78
        if not g.clip:
            core.draw_text(surf, "tühi  ·  klõpsa failis väärtusel, et see meelde jätta", (x, y + 18), "mono", 13, MUTED)
        for chip in g.clip:
            text = cut(chip["value"], "serif", 18, 200)
            w = core.text(text, "serif", 18, TEXT).get_width() + 44
            rect = pygame.Rect(x, y + 10, w, 32)
            can_paste = self.pick is not None
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, (70, 60, 46) if can_paste else (44, 48, 64), rect, border_radius=9)
            if can_paste:
                pygame.draw.rect(surf, AMBER, rect, 2 if not hover else 3, border_radius=9)
            core.draw_text(surf, text, (x + 12, y + 14), "serif", 18, TEXT)
            if can_paste:
                self.hot.append((rect, ("paste", chip)))
            else:
                core.draw_text(surf, "x", (rect.right - 20, y + 14), "mono", 16, MUTED)
                self.hot.append((pygame.Rect(rect.right - 28, rect.y, 28, 32), ("forget", chip)))
            x += w + 8
        if self.pick:
            core.draw_text(surf, "vali, mis käib tühja kohta", (min(x + 10, core.W - 300), y + 18), "mono", 13, AMBER)

    def draw_viewer(self, surf):
        g = self.game
        f = self.open
        veil = pygame.Surface((core.W, core.H - TOP - CLIP_H))
        veil.fill((10, 10, 16))
        veil.set_alpha(170)
        surf.blit(veil, (0, TOP))
        win = WIN.move(math.sin(self.t * 60) * 6 if self.shake else 0, 0)
        pygame.draw.rect(surf, (12, 12, 18), win.move(6, 8), border_radius=12)
        pygame.draw.rect(surf, PAPER, win, border_radius=12)
        bar = pygame.Rect(win.x, win.y, win.w, 36)
        pygame.draw.rect(surf, (60, 46, 40), bar, border_top_left_radius=12, border_top_right_radius=12)
        core.draw_text(surf, cut(f["name"], "mono", 15, win.w - 330), (win.x + 16, win.y + 9), "mono", 15, PAPER)
        self.hot.append((win, ("noop",)))
        self.button(surf, pygame.Rect(win.right - 40, win.y + 5, 30, 26), "x", ("close",), PAPER, 17)
        self.button(surf, pygame.Rect(win.right - 150, win.y + 5, 46, 26), "<", ("step", -1), PAPER, 17)
        self.button(surf, pygame.Rect(win.right - 98, win.y + 5, 46, 26), ">", ("step", 1), PAPER, 17)
        self.button(surf, pygame.Rect(win.right - 316, win.y + 5, 156, 26), "samast kogust", ("find", "group", f["group"]), PAPER, 13)

        left = pygame.Rect(win.x + 20, win.y + 52, 430, 430)
        hidden_text = g.blank(f, "__text")
        if f.get("image"):
            pygame.draw.rect(surf, (226, 216, 190), left)
            img = core.image(f["image"], scale=1)
            k = min(left.w / img.get_width(), left.h / img.get_height())
            key = ("fit", f["id"])
            if key not in self.thumbs:
                self.thumbs[key] = pygame.transform.smoothscale(img, (round(img.get_width() * k), round(img.get_height() * k)))
            fitted = self.thumbs[key]
            surf.blit(fitted, fitted.get_rect(center=left.center))
            pygame.draw.rect(surf, INK, left, 2)
        else:
            self.draw_document(surf, f, left, hidden_text)

        # fields
        x, y = left.right + 26, win.y + 56
        width = win.right - x - 24
        mouse = pygame.mouse.get_pos()
        for label, value in f["fields"]:
            if not value and not g.blank(f, label):
                continue
            core.draw_text(surf, label, (x, y + 4), "mono", 13, (130, 112, 96))
            vx = x + 118
            if g.blank(f, label):
                rect = pygame.Rect(vx - 6, y - 2, 300, 28)
                on = self.pick == label
                blink = 0.5 + 0.5 * math.sin(self.t * 5)
                pygame.draw.rect(surf, (236, 190, 110) if on else (150 + int(40 * blink), 214, 204), rect, border_radius=6)
                core.draw_text(surf, "vali alt mälust" if on else "- - - puudub - - -", (vx + 2, y + 3), "mono", 14, INK)
                self.hot.append((rect, ("blank", label)))
            else:
                shown = cut(value, "serif", 19, width - 118 - 54)
                img = core.text(shown, "serif", 19, INK)
                rect = pygame.Rect(vx - 4, y - 2, img.get_width() + 8, 28)
                if rect.collidepoint(mouse):
                    pygame.draw.rect(surf, (250, 226, 170), rect, border_radius=6)
                surf.blit(img, (vx, y))
                self.hot.append((rect, ("copy", label, value)))
                if label not in ("Number", "Kirje", "Viide", "Projekti nr"):
                    frect = pygame.Rect(win.right - 70, y, 46, 22)
                    hover = frect.collidepoint(mouse)
                    core.draw_text(surf, "otsi", (frect.x + 6, frect.y + 3), "mono", 12, (160, 66, 52) if hover else (150, 132, 116))
                    self.hot.append((frect, ("find", label, value)))
            y += 31

        # texts under the fields, scrollable
        y += 6
        area = pygame.Rect(x, y, width, win.bottom - 58 - y)
        if f["kind"] == "museaal":
            lines = []
            for kind, text in f["texts"]:
                lines.append(("mono", kind.upper()))
                lines += [("serif", l) for l in core.wrap(text, "serif", 17, area.w)]
                lines.append(("serif", ""))
            fit = max(1, area.h // 21)
            self.text_scroll = max(0, min(self.text_scroll, max(0, len(lines) - fit)))
            for i, (kind, line) in enumerate(lines[self.text_scroll:self.text_scroll + fit]):
                if kind == "mono":
                    core.draw_text(surf, line, (area.x, area.y + i * 21 + 4), "mono", 12, (160, 66, 52))
                else:
                    core.draw_text(surf, line, (area.x, area.y + i * 21), "serif", 17, INK)
            if len(lines) > fit:
                core.draw_text(surf, "keri hiirerattaga", (area.right - 130, area.bottom + 2), "mono", 11, (150, 132, 116))

        # trip, feedback, stamp, source
        case = g.case_for(f)
        if case and case.get("trip") and g.broken(f) and not g.has_trip_facts(f):
            rect = pygame.Rect(left.x + 60, left.bottom - 76, left.w - 120, 46)
            self.button(surf, rect, "astu kirje sisse", ("trip", case["trip"]), (160, 66, 52), 18)
        if self.note_t:
            core.draw_text(surf, self.note, (win.x + 22, win.bottom - 82), "italic", 19, (160, 66, 52), alpha=int(255 * min(1, self.note_t)))
        if self.stamp_t is not None or (f["id"] in g.fixed):
            k = 1.0 if self.stamp_t is None else min(1.0, self.stamp_t / 0.25)
            label = core.text("PARANDATUD", "mono", 34, (160, 66, 52))
            base = pygame.Surface((label.get_width() + 30, label.get_height() + 16), pygame.SRCALPHA)
            pygame.draw.rect(base, (160, 66, 52), base.get_rect(), 4, border_radius=8)
            base.blit(label, (15, 9))
            stamp = pygame.transform.rotozoom(base, 9, 1 + (1 - k) * 0.7)
            stamp.set_alpha(int(230 * k))
            surf.blit(stamp, stamp.get_rect(center=(left.centerx, left.bottom - 40)))
        core.draw_text(surf, cut(f"Allikas: {f['source']}", "mono", 12, win.w - 40), (win.x + 22, win.bottom - 46), "mono", 12, (130, 112, 96))
        rights = f.get("rights") or "õigused kontrollimata"
        core.draw_text(surf, cut(rights, "mono", 12, win.w - 40), (win.x + 22, win.bottom - 28), "mono", 12, (130, 112, 96))

    def draw_document(self, surf, f, left, hidden):
        pygame.draw.rect(surf, (250, 244, 226), left)
        pygame.draw.rect(surf, (200, 186, 160), left, 2)
        if f["kind"] == "ehitusprojekt":
            pygame.draw.rect(surf, (36, 70, 120), left.inflate(-24, -24))
            core.draw_text(surf, f["title"], (left.centerx, left.y + 150), "mono", 17, (228, 238, 250), center=True)
            core.draw_text(surf, "plaani skaneering on Rahvusarhiivis", (left.centerx, left.y + 190), "mono", 13, (170, 190, 220), center=True)
            core.draw_text(surf, "ra.ee/apps/hooned", (left.centerx, left.y + 212), "mono", 13, (170, 190, 220), center=True)
            return
        text = f["texts"][0][1] if f["texts"] else ""
        lines = []
        for para in text.split("\n"):
            lines += core.wrap(para.strip(), "italic", 17, left.w - 36)
        fit = (left.h - 30) // 21
        self.text_scroll = max(0, min(self.text_scroll, max(0, len(lines) - fit)))
        for i, line in enumerate(lines[self.text_scroll:self.text_scroll + fit]):
            if hidden:
                # unreadable: blocks where the words should be
                w = core.font("italic", 17).size(line)[0]
                for bx in range(0, w, 14):
                    if (bx * 7 + i * 13) % 5:
                        pygame.draw.rect(surf, (150, 214, 204) if (bx + i + int(self.t * 6)) % 3 else (200, 190, 170),
                                         (left.x + 18 + bx, left.y + 20 + i * 21, 11, 14))
            else:
                core.draw_text(surf, line, (left.x + 18, left.y + 16 + i * 21), "italic", 17, INK)
        if hidden:
            pygame.draw.rect(surf, (250, 244, 226), (left.centerx - 110, left.bottom - 124, 220, 30))
            core.draw_text(surf, "tekst on loetamatu", (left.centerx, left.bottom - 109), "mono", 15, (160, 66, 52), center=True)

    def draw_liis(self, surf):
        g = self.game
        if not self.control:
            return
        if not g.liis:
            if g.cases and len(g.fixed) >= g.cases:
                rect = pygame.Rect(core.W - 300, core.H - CLIP_H - 62, 280, 46)
                core.add_glow(surf, rect.center, 160, AMBER, 0.3 + 0.1 * math.sin(self.t * 3))
                self.button(surf, rect, "ava näitus  >", ("open_show",), AMBER, 18)
            return
        text = g.liis[0]
        lines = core.wrap(text, "serif", 21, 400)
        h = 62 + len(lines) * 26
        rect = pygame.Rect(core.W - 460, core.H - CLIP_H - h - 14, 444, h)
        pygame.draw.rect(surf, (10, 10, 16), rect.move(4, 6), border_radius=14)
        pygame.draw.rect(surf, (40, 60, 62), rect, border_radius=14)
        pygame.draw.rect(surf, TEAL, rect, 2, border_radius=14)
        core.draw_text(surf, f"{LIIS}  ·  terminal", (rect.x + 20, rect.y + 12), "mono", 13, TEAL)
        for i, line in enumerate(lines):
            core.draw_text(surf, line, (rect.x + 20, rect.y + 34 + i * 26), "serif", 21, TEXT)
        more = f"tühik >  ({len(g.liis) - 1} veel)" if len(g.liis) > 1 else "tühik >"
        core.draw_text(surf, more, (rect.right - 20 - core.text(more, "mono", 13, AMBER).get_width(), rect.bottom - 24),
                       "mono", 13, AMBER, alpha=int(180 + 70 * math.sin(self.t * 4)))
        self.hot.append((rect, ("liis",)))


class Title:
    """The title sits over the live file listing."""

    def __init__(self, game):
        self.game = game
        self.t = 0.0
        self.desk = Desk(game, control=False)
        self.veil = pygame.Surface((core.W, core.H))
        self.veil.fill((14, 14, 22))
        self.veil.set_alpha(190)

    def update(self, dt, events):
        self.t += dt
        self.desk.update(dt, [])
        self.desk.scroll = (self.t * 14) % 2400
        if self.t > 0.5 and (core.pressed_confirm(events) or core.clicked(events)):
            self.desk.scroll = 0
            self.game.go(lambda: Desk(self.game))

    def draw(self, surf):
        self.desk.draw(surf)
        surf.blit(self.veil, (0, 0))
        core.draw_text(surf, "ARHIIVIHOIDJA", (core.W / 2, 220), "bold", 100, core.CREAM, center=True)
        core.draw_text(surf, "vaim muuseumi serveris", (core.W / 2, 300), "italic", 34, AMBER, center=True)
        core.draw_text(surf, f"{len(self.game.files)} päris kirjet. Mõni neist on katki.", (core.W / 2, 370), "serif", 24, MUTED, center=True)
        a = int(160 + 90 * math.sin(self.t * 2.4))
        core.draw_text(surf, "vajuta tühikut", (core.W / 2, 590), "mono", 22, core.CREAM, center=True, alpha=a)
        core.draw_text(surf, "M – muusika sisse/välja", (core.W / 2, 690), "mono", 14, MUTED, center=True)
