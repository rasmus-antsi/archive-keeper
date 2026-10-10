"""A shelf, opened: browse its real records, and step into the ones that hold a memory.

This is an overlay on top of the archive room.
"""
import pygame

from .. import assets, settings, ui
from ..scene import Scene

BOX = pygame.Rect(40, 36, settings.W - 80, settings.H - 86)
LIST_W = 300
ROW_H = 26
ROWS = (BOX.height - 76) // ROW_H


class Reader(Scene):
    see_through = True

    def __init__(self, game, shelf):
        super().__init__(game)
        self.shelf = shelf
        self.entries = self.content.shelf_entries(shelf)
        self.cursor = min(self.state.shelf_cursor.get(shelf["id"], 0), max(0, len(self.entries) - 1))
        self.top_row = 0
        self.dim = pygame.Surface((settings.W, settings.H), pygame.SRCALPHA)
        self.dim.fill((8, 8, 12, 190))

    def row_rect(self, i):
        return pygame.Rect(BOX.left + 14, BOX.top + 62 + (i - self.top_row) * ROW_H, LIST_W - 20, ROW_H)

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

    def draw_ui(self, screen):
        screen.blit(self.dim, (0, 0))
        ui.panel(screen, BOX, (30, 26, 28), 245, border=(92, 78, 64))
        ui.draw_text(screen, self.shelf["label"], (BOX.left + 22, BOX.top + 12), "title", 34, settings.WARM)
        count = ui.text(f"{len(self.entries)} records", "mono", 13, settings.DIM)
        screen.blit(count, (BOX.right - 24 - count.get_width(), BOX.top + 28))
        pygame.draw.line(screen, (92, 78, 64), (BOX.left + LIST_W, BOX.top + 58), (BOX.left + LIST_W, BOX.bottom - 14))

        for i in range(self.top_row, min(len(self.entries), self.top_row + ROWS)):
            entry, rect = self.entries[i], self.row_rect(i)
            doc = entry["doc"]
            if i == self.cursor:
                pygame.draw.rect(screen, (70, 58, 50), rect, border_radius=4)
            color = settings.CREAM
            if doc:
                color = settings.DIM if doc["id"] in self.state.solved else settings.TEAL
            name = ("* " if doc else "") + entry["title"]
            while len(name) > 4 and assets.font("body", 18).size(name)[0] > rect.width - 12:
                name = name[:-2].rstrip() + "…"
            ui.draw_text(screen, name, (rect.left + 6, rect.top + 2), "body", 18, color)
        if len(self.entries) > ROWS:
            track = pygame.Rect(BOX.left + 6, BOX.top + 62, 3, ROWS * ROW_H)
            k = ROWS / len(self.entries)
            bar = pygame.Rect(track.left, track.top + track.height * self.top_row / len(self.entries), 3, track.height * k)
            pygame.draw.rect(screen, (92, 78, 64), bar)

        if self.entries:
            self.draw_entry(screen, self.entries[self.cursor])
        ui.hint(screen, "W/S or wheel — browse · Enter — step into a memory (*) · Esc — close")

    def draw_entry(self, screen, entry):
        record, doc = entry["record"], entry["doc"]
        x = BOX.left + LIST_W + 24
        width = BOX.right - x - 24
        y = BOX.top + 62
        role = "title" if doc else "bold"       # shelf-marks like "ERM B 185:6" are unreadable in fraktur
        y = ui.draw_wrapped(screen, entry["title"], (x, y), width, role, 30, settings.CREAM, limit=2) + 2
        if entry["sub"]:
            y = ui.draw_text(screen, entry["sub"], (x, y), "italic", 19, settings.DIM).bottom + 8

        if doc:
            solved = doc["id"] in self.state.solved
            ui.panel(screen, (x, y, width, 62), (24, 44, 46) if not solved else (36, 36, 40), 255, border=settings.TEAL if not solved else None)
            if solved:
                ui.draw_text(screen, "Restored. The memory is whole again.", (x + 16, y + 18), "body", 22, settings.DIM)
            else:
                ui.draw_text(screen, "A memory is caught in this record.", (x + 16, y + 6), "body", 22, settings.CREAM)
                ui.draw_text(screen, "Enter — step inside", (x + 16, y + 34), "mono", 16, settings.WARM, alpha=ui.blink())
            y += 76

        img = assets.photo(record["image"], (width, 230)) if record.get("image") else None
        if img:
            screen.blit(img, (x, y))
            y += img.get_height() + 12

        for label, value in record.get("fields", []):
            if not value or y > BOX.bottom - 90:
                continue
            ui.draw_text(screen, label.upper(), (x, y + 4), "mono", 13, settings.DIM)
            y = ui.draw_wrapped(screen, value, (x + 130, y), width - 130, "body", 19, settings.CREAM, gap=1, limit=2) + 2

        for kind, body in record.get("texts", []):
            line = assets.font("italic", 18).get_linesize() + 1
            room = (BOX.bottom - 64 - y) // line
            if room < 2:
                break
            y = ui.draw_wrapped(screen, body, (x, y + 8), width, "italic", 18, settings.PAPER, gap=1, limit=room) + 4

        source = record.get("source")
        if source:
            ui.draw_text(screen, source, (x, BOX.bottom - 46), "mono", 12, settings.DIM)
        if record.get("rights"):
            ui.draw_text(screen, record["rights"], (x, BOX.bottom - 30), "mono", 12, settings.DIM)
