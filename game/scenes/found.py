"""The right thing has been handed over: it comes down, large, onto the page it was
missing from, and the page fills in again.

This is an overlay (see game/scene.py): the place waits, darkened, behind it.

The page is the document's "record" picture. A request in data/documents/*.json may
name the "page" as it looks with its thing back, and the "page_spot" [x, y] on it
(in the picture's own pixels) where the middle of the thing belongs. Without them the
thing rests in the middle of the page with its name under it.
"""
import pygame

from .. import assets, effects, settings, ui
from ..scene import Overlay
from .memory import item_image

SCALE = 4             # how much the page is enlarged
SHEET = (664, 816)    # the size of a page, for a document that has no picture of one
DROP = 0.7            # seconds for the thing to come down onto the page
FILL = 0.8            # seconds for the page to fill in after that
FALL = 420            # how far above its place the thing starts


class Found(Overlay):
    DIM = 0.86

    def __init__(self, game, doc, item, request, after):
        super().__init__(game)
        self.after = after          # runs once this has closed
        self.t = 0.0
        blank = doc.get("record", {}).get("image", "")
        blank = assets.sprite(blank, scale=SCALE) if assets.optional(blank) else None
        filled = request.get("page", "")
        self.page = assets.sprite(filled, scale=SCALE) if assets.optional(filled) else None
        self.thing = item_image(item, 400)
        self.sheet = pygame.Rect((0, 0), blank.get_size() if blank else SHEET)
        self.sheet.center = (settings.W // 2, settings.H // 2 - 24)
        spot = request.get("page_spot")
        self.rest = (self.sheet.x + spot[0] * SCALE, self.sheet.y + spot[1] * SCALE) if spot else self.sheet.center
        self.label = None if self.page else item["label"]
        if blank:
            self.backdrop.blit(blank, self.sheet)
        else:
            ui.panel(self.backdrop, self.sheet, settings.PAPER, 255, radius=10)

    @property
    def settled(self):
        return self.t >= DROP + FILL

    def handle(self, dt, events):
        self.t += dt
        if ui.confirm(events) or ui.clicked(events):
            if self.settled:
                self.close(then=self.after)
            else:
                self.t = DROP + FILL        # the first press goes straight to the finished page

    def paint(self, screen):
        x, y = self.rest
        up = round((1 - effects.ease(self.t / DROP)) * FALL)
        screen.blit(self.thing, self.thing.get_rect(center=(x, y - up)))
        filled = round(255 * max(0.0, min(1.0, (self.t - DROP) / FILL)))
        if self.page and filled:
            self.page.set_alpha(filled)
            screen.blit(self.page, self.sheet)
            self.page.set_alpha(255)
        if self.label and filled:
            ui.draw_text(screen, self.label, (x, y + self.thing.get_height() // 2 + 50), "title", 48, settings.INK,
                         center=True, alpha=filled)
        effects.whiten(screen, 0.55 * (1 - abs(self.t - DROP) / 0.2))      # a flash as it lands
        if self.settled:
            self.hint(screen, "memory.found")
