"""Game state, scene switching with a fade, and the sparse background music."""

import random

import pygame

from . import core, layout


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.records = core.load_records()
        self.by_id = {r["id"]: r for r in self.records}
        self.black = pygame.Surface((core.W, core.H))
        self.music_on = True
        self.music_t = 2.0
        self.note = 4
        self.echo = None
        self.restart()

    def restart(self):
        from .home import Title
        self.restored = []          # record ids, in the order they were restored
        self.unlocked = {w for w, d in layout.WINGS.items() if d["unlock"] == 0}
        self.pos = pygame.Vector2(layout.START)
        self.home_pos = None
        self.seen_intro = False
        self.flags = {}             # trip id -> set of flag words
        # the blanks of every record that has a trip: found out there, then placed on its card
        self.fragments = []
        for rec in self.records:
            if "trip" in rec:
                for idx, blank in enumerate(rec["blanks"]):
                    self.fragments.append({"rid": rec["id"], "idx": idx, "wing": rec["wing"], "value": blank["value"],
                                           "line": blank["line"], "state": "world"})
        self.next = None
        self.fade = 1.0
        self.scene = Title(self)

    def held(self, wing=None):
        return [f for f in self.fragments if f["state"] == "held" and wing in (None, f["wing"])]

    def restored_in(self, wing):
        return sum(1 for rid in self.restored if self.by_id[rid]["wing"] == wing)

    def go(self, factory):
        """Fade out, build the next scene, fade in."""
        if self.next is None:
            self.next = factory

    def music(self, dt, events):
        """A few soft plucked notes wandering over a pentatonic scale. M mutes."""
        if core.pressed(events, pygame.K_m):
            self.music_on = not self.music_on
        if not self.music_on:
            return
        self.music_t -= dt
        if self.echo and self.music_t < self.echo[0]:
            core.play(f"note_{self.echo[1]}.ogg", 0.14)
            self.echo = None
        if self.music_t <= 0:
            self.note = max(0, min(8, self.note + random.choice((-2, -1, -1, 1, 1, 2))))
            core.play(f"note_{self.note}.ogg", random.uniform(0.16, 0.26))
            self.music_t = random.choice((0.8, 1.2, 1.6, 2.4, 3.2))
            if random.random() < 0.3 and self.note + 2 <= 8:
                self.echo = (self.music_t - 0.2, self.note + 2)

    def update(self, dt, events):
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
        self.music(dt, events)
        if self.next:
            self.fade += dt / 0.4
            if self.fade >= 1:
                self.fade = 1.0
                self.scene = self.next()
                self.next = None
            return
        self.fade = max(0.0, self.fade - dt / 0.5)
        self.scene.update(dt, events)

    def draw(self):
        self.scene.draw(self.screen)
        if self.fade > 0:
            self.black.set_alpha(int(255 * core.ease(self.fade)))
            self.screen.blit(self.black, (0, 0))
