"""Looking inside a chest, cupboard or barrel in a memory: what is in it, and taking one thing.

This is an overlay: it keeps a darkened copy of the place it was opened from.
"""
import pygame

from .. import settings, ui
from ..scene import Scene
from .memory import item_image

BOX = pygame.Rect(0, 0, 1240, 560)
BOX.center = (settings.W // 2, settings.H // 2 - 20)
SLOT = 240


class Inside(Scene):
    def __init__(self, game, memory, container):
        super().__init__(game)
        self.memory = memory
        self.container = container
        self.items = memory.contents(container)
        self.cursor = 0
        self.backdrop = game.screen.copy()
        dim = pygame.Surface(self.backdrop.get_size(), pygame.SRCALPHA)
        dim.fill((8, 8, 12, 190))
        self.backdrop.blit(dim, (0, 0))
        ui.panel(self.backdrop, BOX, (58, 42, 34), 255, radius=20, border=(132, 98, 66))
        ui.panel(self.backdrop, BOX.inflate(-60, -230).move(0, 30), (34, 25, 22), 255, radius=12)

    def slot(self, i):
        rect = pygame.Rect(0, 0, SLOT, SLOT)
        rect.center = (BOX.centerx + (i - (len(self.items) - 1) / 2) * (SLOT + 30), BOX.centery + 30)
        return rect

    def update(self, dt, events):
        if ui.pressed(events, *ui.BACK, pygame.K_q):
            self.scenes.pop()
            return
        take = ui.confirm(events)
        if self.items:
            move = ui.pressed(events, pygame.K_RIGHT, pygame.K_d) - ui.pressed(events, pygame.K_LEFT, pygame.K_a)
            self.cursor = (self.cursor + move) % len(self.items)
            click = ui.clicked(events)
            for i in range(len(self.items)):
                if click and self.slot(i).collidepoint(click):
                    self.cursor, take = i, True
        if take:
            if self.items:
                self.memory.take(self.items[self.cursor])
            self.scenes.pop()

    def draw(self, screen):
        screen.blit(self.backdrop, (0, 0))
        ui.draw_text(screen, self.container.label.capitalize(), (BOX.centerx, BOX.top + 70), "title", 72, settings.WARM,
                     center=True)
        if not self.items:
            ui.draw_text(screen, "Tühi. Ainult tolm.", (BOX.centerx, BOX.centery + 30), "italic", 44, settings.DIM,
                         center=True)
            ui.hint(screen, "E või Esc — sulge")
            return
        for i, item in enumerate(self.items):
            rect = self.slot(i)
            if i == self.cursor:
                pygame.draw.rect(screen, (92, 68, 50), rect, border_radius=14)
                pygame.draw.rect(screen, settings.WARM, rect, 4, border_radius=14)
            img = item_image(item, SLOT - 40)
            screen.blit(img, img.get_rect(center=rect.center))
        ui.draw_text(screen, self.items[self.cursor]["label"], (BOX.centerx, BOX.bottom - 62), "body", 44,
                     settings.CREAM, center=True)
        ui.hint(screen, "A/D — vali · E — võta kaasa · Esc — sulge")
