"""Looking inside a chest, cupboard or barrel in a memory: what is in it, and taking one thing.

This is an overlay (see game/scene.py): the place it was opened in waits, darkened, behind it.
"""
import pygame

from .. import assets, settings, ui
from ..scene import Overlay
from .memory import item_image

BOX = pygame.Rect(0, 0, 1240, 640)
BOX.center = (settings.W // 2, settings.H // 2 - 20)
SLOT = 320


def warm_up(doc):
    """Enlarge every thing of a memory to the size the slots show it at, behind the loading bar."""
    for item in doc["items"]:
        item_image(item, SLOT - 32)


class Inside(Overlay):
    DIM = 0.75

    def __init__(self, game, memory, container):
        super().__init__(game)
        self.memory = memory
        self.container = container
        self.items = memory.contents(container)
        self.cursor = 0
        ui.panel(self.backdrop, BOX, (58, 42, 34), 255, radius=20, border=(132, 98, 66))
        ui.panel(self.backdrop, BOX.inflate(-60, -230).move(0, 30), (34, 25, 22), 255, radius=12)
        ui.draw_text(self.backdrop, container.label.capitalize(), (BOX.centerx, BOX.top + 70), "title", 72,
                     settings.WARM, center=True)

    def slot(self, i):
        rect = pygame.Rect(0, 0, SLOT, SLOT)
        rect.center = (BOX.centerx + (i - (len(self.items) - 1) / 2) * (SLOT + 30), BOX.centery + 30)
        return rect

    def choose(self, i):
        if i != self.cursor:
            self.cursor = i
            assets.play("tick.ogg", 0.5)

    def handle(self, dt, events):
        if ui.pressed(events, *ui.BACK, pygame.K_q):
            self.close()
            return
        take = ui.confirm(events)
        if self.items:
            move = ui.pressed(events, *ui.RIGHT) - ui.pressed(events, *ui.LEFT)
            self.choose((self.cursor + move) % len(self.items))
            over, click = ui.pointed(events), ui.clicked(events)
            for i in range(len(self.items)):
                if over and self.slot(i).collidepoint(over):
                    self.choose(i)
                if click and self.slot(i).collidepoint(click):
                    self.cursor, take = i, True
        if take:
            if self.items:
                self.memory.take(self.items[self.cursor])
            self.close()

    def paint(self, screen):
        if not self.items:
            ui.draw_text(screen, self.text("memory.empty"), (BOX.centerx, BOX.centery + 30), "pixel", 44, settings.DIM,
                         center=True)
            self.hint(screen, "memory.close")
            return
        for i, item in enumerate(self.items):
            rect = self.slot(i)
            if i == self.cursor:
                pygame.draw.rect(screen, (92, 68, 50), rect, border_radius=14)
                pygame.draw.rect(screen, settings.WARM, rect, 4, border_radius=14)
            img = item_image(item, SLOT - 32)
            screen.blit(img, img.get_rect(center=rect.center))
        ui.draw_text(screen, self.items[self.cursor]["label"], (BOX.centerx, BOX.bottom - 62), "pixel", 44,
                     settings.CREAM, center=True)
        self.hint(screen, "memory.take")
