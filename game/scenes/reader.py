"""A shelf, opened: browse its real records, and step into the ones that hold a memory.

This is an overlay (see game/scene.py): the room it was opened from waits, darkened, behind it.
"""
import random

import pygame

from .. import assets, settings, ui
from ..scene import Overlay

BOX = pygame.Rect(110, 60, settings.W - 220, settings.H - 150)
LIST_W = 560
ROW_H = 44
TOP = 110                                   # room for the shelf's name above the list
ROWS = (BOX.height - TOP - 24) // ROW_H
PAGE = pygame.Rect(BOX.left + LIST_W + 24, BOX.top + TOP - 14, BOX.width - LIST_W - 48, BOX.height - TOP - 10)
MARGIN = 36                                 # between the edge of the page and what is written on it
PHOTO_H = 380
FADED = (120, 104, 90)                      # secondary ink on the paper
SETTLE = 0.12                               # seconds on one record before its sharp photograph is fetched
_last_rustle = 0


class Reader(Overlay):
    def __init__(self, game, shelf):
        super().__init__(game)
        self.shelf = shelf
        self.entries = self.content.shelf_entries(shelf)
        self.cursor = min(self.state.shelf_cursor.get(shelf["id"], 0), max(0, len(self.entries) - 1))
        self.top_row = max(0, min(self.cursor - ROWS // 2, len(self.entries) - ROWS))
        self.hover = None               # the row the mouse is on
        self.rested = 0.0               # seconds since the cursor last moved
        self.wheel = 0.0                # wheel movement not yet turned into whole rows
        self.keys = ui.Repeat()
        self.names = {}                 # row -> its title, cut to fit
        rustle()
        ui.panel(self.backdrop, BOX, (30, 26, 28), 250, radius=20, border=(92, 78, 64))
        ui.draw_text(self.backdrop, shelf["label"], (BOX.left + 40, BOX.top + 22), "title", 60, settings.WARM)
        count = ui.text(self.text("reader.count", n=len(self.entries)), "mono", 22, settings.DIM)
        self.backdrop.blit(count, (BOX.right - 40 - count.get_width(), BOX.top + 50))
        # the open record is a sheet of paper with a dog-eared corner
        fold = 70
        pygame.draw.polygon(self.backdrop, settings.PAPER, [PAGE.topleft, PAGE.topright, (PAGE.right, PAGE.bottom - fold),
                                                            (PAGE.right - fold, PAGE.bottom), PAGE.bottomleft])
        pygame.draw.polygon(self.backdrop, (196, 182, 152), [(PAGE.right, PAGE.bottom - fold), (PAGE.right - fold, PAGE.bottom),
                                                             (PAGE.right - fold, PAGE.bottom - fold)])

    # ---------------------------------------------------------------- where things are

    def row_rect(self, i):
        return pygame.Rect(BOX.left + 24, BOX.top + TOP + (i - self.top_row) * ROW_H, LIST_W - 40, ROW_H)

    def visible(self):
        return range(self.top_row, min(len(self.entries), self.top_row + ROWS))

    def row_at(self, pos):
        return next((i for i in self.visible() if self.row_rect(i).collidepoint(pos)), None)

    def enter_rect(self):
        """The 'step inside' box of a record that holds a memory."""
        return pygame.Rect(PAGE.left + MARGIN, BOX.top + TOP + 110, PAGE.width - 2 * MARGIN, 104)

    # ---------------------------------------------------------------- loop

    def handle(self, dt, events):
        if ui.pressed(events, *ui.BACK, pygame.K_q):
            self.state.shelf_cursor[self.shelf["id"]] = self.cursor
            self.close()
            return
        if not self.entries:
            return
        move = self.keys.steps(dt, events, ui.UP, ui.DOWN)
        move += 8 * (ui.pressed(events, pygame.K_PAGEDOWN) - ui.pressed(events, pygame.K_PAGEUP))
        move += len(self.entries) * (ui.pressed(events, pygame.K_END) - ui.pressed(events, pygame.K_HOME))
        for e in events:
            if e.type == pygame.MOUSEWHEEL:          # a touchpad sends many small movements; a wheel sends whole notches
                self.wheel -= getattr(e, "precise_y", e.y)
        move += int(self.wheel)
        self.wheel -= int(self.wheel)

        over = ui.pointed(events)
        if over:
            self.hover = self.row_at(over)
        enter = ui.confirm(events)
        click = ui.clicked(events)
        before = self.cursor
        if click:
            row = self.row_at(click)
            if row is not None:         # a second click on a record that holds a memory steps into it
                enter = enter or (row == self.cursor and self.entries[row]["doc"] is not None)
                self.cursor = row
            elif self.enter_rect().collidepoint(click):
                enter = True
        self.cursor = max(0, min(len(self.entries) - 1, self.cursor + move))
        self.rested += dt
        if self.cursor != before:
            self.rested = 0.0
            rustle()
        self.top_row = max(self.cursor - ROWS + 1, min(self.top_row, self.cursor))
        doc = self.entries[self.cursor]["doc"]
        if enter and doc and doc["id"] not in self.state.solved:
            self.step_into(doc)

    def step_into(self, doc):
        from .memory import Memory
        self.state.shelf_cursor[self.shelf["id"]] = self.cursor
        assets.play("enter.ogg", 0.5)
        self.scenes.go(lambda: Memory(self.game, doc), "spiral")

    # ---------------------------------------------------------------- drawing

    def paint(self, screen):
        for i in self.visible():
            entry, rect = self.entries[i], self.row_rect(i)
            doc = entry["doc"]
            if i == self.cursor:
                pygame.draw.rect(screen, (70, 58, 50), rect, border_radius=6)
            elif i == self.hover:
                pygame.draw.rect(screen, (46, 40, 40), rect, border_radius=6)
            color = settings.CREAM
            if doc:
                color = settings.DIM if doc["id"] in self.state.solved else settings.TEAL
            ui.draw_text(screen, self.row_name(i, rect.width - 20), (rect.left + 10, rect.top + 4), "body", 30, color)
        if len(self.entries) > ROWS:
            track = pygame.Rect(BOX.left + 10, BOX.top + TOP, 5, ROWS * ROW_H)
            bar = pygame.Rect(track.left, track.top + track.height * self.top_row / len(self.entries), 5,
                              track.height * ROWS / len(self.entries))
            pygame.draw.rect(screen, (92, 78, 64), bar)

        if self.entries:
            self.draw_entry(screen, self.entries[self.cursor])
        self.hint(screen, "reader.hint")

    def row_name(self, i, width):
        if i not in self.names:
            entry = self.entries[i]
            self.names[i] = ui.fit(("* " if entry["doc"] else "") + entry["title"], "body", 30, width)
        return self.names[i]

    def picture(self, record, box):
        """The record's photograph. Fetching a sharp one takes a moment, so while the player
        is still flicking through the list they get the small thumbnail, enlarged."""
        name = record["image"]
        if self.rested >= SETTLE or assets.photo_ready(name, box):
            return assets.photo(name, box)
        return assets.photo(record["thumb"], box) if record.get("thumb") else None

    def draw_entry(self, screen, entry):
        record, doc = entry["record"], entry["doc"]
        x = PAGE.left + MARGIN
        width = PAGE.width - 2 * MARGIN
        y = BOX.top + TOP
        role = "title" if doc else "bold"       # shelf-marks like "ERM B 185:6" are unreadable in fraktur
        y = ui.draw_wrapped(screen, entry["title"], (x, y), width, role, 48, settings.INK, limit=2) + 2
        if entry["sub"]:
            y = ui.draw_text(screen, entry["sub"], (x, y), "italic", 30, FADED).bottom + 14

        if doc:
            box = self.enter_rect()
            solved = doc["id"] in self.state.solved
            ui.panel(screen, box, (36, 36, 40) if solved else (24, 44, 46), 255, border=None if solved else settings.TEAL)
            if solved:
                ui.draw_text(screen, self.text("reader.restored"), (box.x + 28, box.y + 30), "body", 36, settings.DIM)
            else:
                ui.draw_text(screen, self.text("reader.caught"), (box.x + 28, box.y + 10), "body", 36)
                ui.draw_text(screen, self.text("reader.enter"), (box.x + 28, box.y + 58), "mono", 26, settings.WARM,
                             alpha=ui.blink())
            y = box.bottom + 24

        img = None
        if doc and record.get("image"):
            # the team's own pixel-art page: blank while the memory is lost, filled in once restored
            name = record.get("image_restored") if doc["id"] in self.state.solved else None
            img = assets.sprite(name or record["image"], scale=2)
        elif record.get("image"):
            img = self.picture(record, (width, PHOTO_H))
        if img:
            screen.blit(img, (x, y))
            y += img.get_height() + 20

        for label, value in record.get("fields", []):
            if not value or y > BOX.bottom - 125:
                continue
            ui.draw_text(screen, label.upper(), (x, y + 8), "mono", 20, FADED)
            y = ui.draw_wrapped(screen, value, (x + 210, y), width - 210, "body", 30, settings.INK, gap=1, limit=2) + 4

        for kind, body in record.get("texts", []):
            line = assets.font("italic", 28).get_linesize() + 1
            room = (BOX.bottom - 110 - y) // line
            if room < 2:
                break
            y = ui.draw_wrapped(screen, body, (x, y + 12), width, "italic", 28, (70, 56, 50), gap=1, limit=room) + 6

        if record.get("source"):
            ui.draw_text(screen, record["source"], (x, BOX.bottom - 76), "mono", 18, FADED)
        if record.get("rights"):
            ui.draw_text(screen, record["rights"], (x, BOX.bottom - 48), "mono", 18, FADED)


def rustle():
    """A page turning, but not a whole flock of them when the list is scrolled quickly."""
    global _last_rustle
    now = pygame.time.get_ticks()
    if now - _last_rustle > 70:
        _last_rustle = now
        assets.play(f"page{random.randint(1, 6)}.ogg", 0.5)
