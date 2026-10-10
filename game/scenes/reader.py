"""A shelf, opened: browse its real records, and step into the ones that hold a memory.

This is an overlay: it keeps a darkened copy of the room it was opened from.
"""
import pygame

from .. import assets, settings, ui
from ..scene import Scene

BOX = pygame.Rect(110, 60, settings.W - 220, settings.H - 150)
LIST_W = 560
ROW_H = 44
TOP = 110                                   # room for the shelf's name above the list
ROWS = (BOX.height - TOP - 24) // ROW_H


class Reader(Scene):
    def __init__(self, game, shelf):
        super().__init__(game)
        self.shelf = shelf
        self.entries = self.content.shelf_entries(shelf)
        self.cursor = min(self.state.shelf_cursor.get(shelf["id"], 0), max(0, len(self.entries) - 1))
        self.top_row = 0
        self.backdrop = game.screen.copy()
        dim = pygame.Surface(self.backdrop.get_size(), pygame.SRCALPHA)
        dim.fill((8, 8, 12, 200))
        self.backdrop.blit(dim, (0, 0))
        ui.panel(self.backdrop, BOX, (30, 26, 28), 250, radius=20, border=(92, 78, 64))

    def row_rect(self, i):
        return pygame.Rect(BOX.left + 24, BOX.top + TOP + (i - self.top_row) * ROW_H, LIST_W - 40, ROW_H)

    def update(self, dt, events):
        if ui.pressed(events, *ui.BACK, pygame.K_q):
            self.close()
            return
        move = ui.pressed(events, pygame.K_DOWN, pygame.K_s) - ui.pressed(events, pygame.K_UP, pygame.K_w)
        move += 8 * (ui.pressed(events, pygame.K_PAGEDOWN) - ui.pressed(events, pygame.K_PAGEUP))
        for e in events:
            if e.type == pygame.MOUSEWHEEL:
                move -= e.y
        click = ui.clicked(events)
        enter = ui.confirm(events)
        if click:
            for i in range(self.top_row, min(len(self.entries), self.top_row + ROWS)):
                if self.row_rect(i).collidepoint(click):
                    enter = enter or (i == self.cursor and self.entries[i]["doc"] is not None)
                    self.cursor = i
            if self.entries and self.enter_rect().collidepoint(click):
                enter = True
        if move and self.entries:
            self.cursor = max(0, min(len(self.entries) - 1, self.cursor + move))
        self.top_row = max(self.cursor - ROWS + 1, min(self.top_row, self.cursor))
        if enter and self.entries:
            doc = self.entries[self.cursor]["doc"]
            if doc and doc["id"] not in self.state.solved:
                self.step_into(doc)

    def close(self):
        self.state.shelf_cursor[self.shelf["id"]] = self.cursor
        self.scenes.pop()

    def step_into(self, doc):
        from .memory import Memory
        self.state.shelf_cursor[self.shelf["id"]] = self.cursor
        assets.play("enter.ogg", 0.5)
        self.scenes.go(lambda: Memory(self.game, doc))

    # ---------------------------------------------------------------- drawing

    def detail_x(self):
        return BOX.left + LIST_W + 40

    def enter_rect(self):
        """The 'step inside' box of a record that holds a memory."""
        x = self.detail_x()
        return pygame.Rect(x, BOX.top + TOP + 110, BOX.right - x - 40, 104)

    def draw(self, screen):
        screen.blit(self.backdrop, (0, 0))
        ui.draw_text(screen, self.shelf["label"], (BOX.left + 40, BOX.top + 22), "title", 60, settings.WARM)
        count = ui.text(f"{len(self.entries)} records", "mono", 22, settings.DIM)
        screen.blit(count, (BOX.right - 40 - count.get_width(), BOX.top + 50))
        pygame.draw.line(screen, (92, 78, 64), (BOX.left + LIST_W, BOX.top + TOP), (BOX.left + LIST_W, BOX.bottom - 24), 2)

        for i in range(self.top_row, min(len(self.entries), self.top_row + ROWS)):
            entry, rect = self.entries[i], self.row_rect(i)
            doc = entry["doc"]
            if i == self.cursor:
                pygame.draw.rect(screen, (70, 58, 50), rect, border_radius=6)
            color = settings.CREAM
            if doc:
                color = settings.DIM if doc["id"] in self.state.solved else settings.TEAL
            ui.draw_text(screen, self.row_name(entry, rect.width - 20), (rect.left + 10, rect.top + 4), "body", 30, color)
        if len(self.entries) > ROWS:
            track = pygame.Rect(BOX.left + 10, BOX.top + TOP, 5, ROWS * ROW_H)
            bar = pygame.Rect(track.left, track.top + track.height * self.top_row / len(self.entries), 5,
                              track.height * ROWS / len(self.entries))
            pygame.draw.rect(screen, (92, 78, 64), bar)

        if self.entries:
            self.draw_entry(screen, self.entries[self.cursor])
        ui.hint(screen, "W/S or wheel — browse · Enter — step into a memory (*) · Esc — close")

    def row_name(self, entry, width):
        if "row" not in entry:
            name = ("* " if entry["doc"] else "") + entry["title"]
            while len(name) > 4 and assets.font("body", 30).size(name)[0] > width:
                name = name[:-2].rstrip() + "…"
            entry["row"] = name
        return entry["row"]

    def draw_entry(self, screen, entry):
        record, doc = entry["record"], entry["doc"]
        x = self.detail_x()
        width = BOX.right - x - 40
        y = BOX.top + TOP
        role = "title" if doc else "bold"       # shelf-marks like "ERM B 185:6" are unreadable in fraktur
        y = ui.draw_wrapped(screen, entry["title"], (x, y), width, role, 48, settings.CREAM, limit=2) + 2
        if entry["sub"]:
            y = ui.draw_text(screen, entry["sub"], (x, y), "italic", 30, settings.DIM).bottom + 14

        if doc:
            box = self.enter_rect()
            solved = doc["id"] in self.state.solved
            ui.panel(screen, box, (36, 36, 40) if solved else (24, 44, 46), 255, border=None if solved else settings.TEAL)
            if solved:
                ui.draw_text(screen, "Restored. The memory is whole again.", (box.x + 28, box.y + 30), "body", 36,
                             settings.DIM)
            else:
                ui.draw_text(screen, "A memory is caught in this record.", (box.x + 28, box.y + 10), "body", 36)
                ui.draw_text(screen, "Enter — step inside", (box.x + 28, box.y + 58), "mono", 26, settings.WARM,
                             alpha=ui.blink())
            y = box.bottom + 24

        img = assets.photo(record["image"], (width, 380)) if record.get("image") else None
        if img:
            screen.blit(img, (x, y))
            y += img.get_height() + 20

        for label, value in record.get("fields", []):
            if not value or y > BOX.bottom - 125:
                continue
            ui.draw_text(screen, label.upper(), (x, y + 8), "mono", 20, settings.DIM)
            y = ui.draw_wrapped(screen, value, (x + 210, y), width - 210, "body", 30, settings.CREAM, gap=1, limit=2) + 4

        for kind, body in record.get("texts", []):
            line = assets.font("italic", 28).get_linesize() + 1
            room = (BOX.bottom - 110 - y) // line
            if room < 2:
                break
            y = ui.draw_wrapped(screen, body, (x, y + 12), width, "italic", 28, settings.PAPER, gap=1, limit=room) + 6

        if record.get("source"):
            ui.draw_text(screen, record["source"], (x, BOX.bottom - 76), "mono", 18, settings.DIM)
        if record.get("rights"):
            ui.draw_text(screen, record["rights"], (x, BOX.bottom - 48), "mono", 18, settings.DIM)
