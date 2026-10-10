"""Game state, scene switching with a fade, and the sparse background music."""
import json
import random

import pygame

from . import core, layout

MEMORY = 7           # how many values the keeper can hold at once


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.records = core.load_records()                 # the twelve shown in the museum epilogue
        self.by_id = {r["id"]: r for r in self.records}
        with open("data/archive.json", encoding="utf-8") as f:
            self.archive = json.load(f)
        with open("data/cases.json", encoding="utf-8") as f:
            self.case_list = json.load(f)
        self.black = pygame.Surface((core.W, core.H))
        self.music_on = True
        self.music_t = 2.0
        self.note = 4
        self.echo = None
        self.restart()

    def restart(self):
        from .desk import Title
        # a fresh copy of every real record; cases blank some of their fields
        self.files = json.loads(json.dumps(self.archive))
        self.file_by_id = {f["id"]: f for f in self.files}
        self.blanks = set()         # (file id, field label) still missing; "__text" hides the text
        self.fixed = []             # file ids, in the order they were repaired
        self.clip = []              # remembered values: {"label", "value"}
        self.liis = []              # messages waiting in the terminal
        self.desk_folder = "*"
        self.fragments = []         # facts a trip can teach, for the trip's checklist
        for case in self.case_list:
            f = self.file_by_id[case["file"]]
            if "record" in case:
                rec = self.by_id[case["record"]]
                for idx, blank in enumerate(rec["blanks"]):
                    f["fields"].append([blank["label"], blank["value"]])
                    self.blanks.add((f["id"], blank["label"]))
                    self.fragments.append({"rid": rec["id"], "idx": idx, "value": blank["value"], "state": "world"})
            for label in case.get("blanks", []):
                self.blanks.add((f["id"], label))
            if case.get("hide_text"):
                self.blanks.add((f["id"], "__text"))
        self.cases = len(self.case_list)
        self.flags = {}             # trip id -> set of flag words
        self.seen_intro = False
        # the museum epilogue
        self.restored = []
        self.unlocked = set()
        self.pos = pygame.Vector2(layout.START)
        self.next = None
        self.fade = 1.0
        self.scene = Title(self)

    # ---------------------------------------------------------------- the archive

    def blank(self, f, label):
        return (f["id"], label) in self.blanks

    def broken(self, f):
        return any(fid == f["id"] and label != "__text" for fid, label in self.blanks)

    def case_for(self, f):
        return next((c for c in self.case_list if c["file"] == f["id"]), None)

    def case_file(self, record_id):
        return next(c["file"] for c in self.case_list if c.get("record") == record_id)

    def has_trip_facts(self, f):
        held = {c["value"] for c in self.clip}
        return all(dict(f["fields"])[label] in held for fid, label in self.blanks if fid == f["id"] and label != "__text")

    def remember(self, label, value):
        self.clip = [c for c in self.clip if c["value"] != value]
        self.clip.append({"label": label, "value": value})
        self.clip = self.clip[-MEMORY:]

    def on_fixed(self):
        """A file is whole again: its text comes back and Liis notices."""
        fid = self.fixed[-1]
        self.blanks.discard((fid, "__text"))
        n = len(self.fixed)
        case = self.case_for(self.file_by_id[fid])
        if case.get("trip"):
            self.liis.append("…Selle teksti kohta ei olnud vastust üheski failis. Kuidas sa seda tegid? Ei, ära ütle.")
        elif n == 1:
            self.liis.append("Üks korras. Nägid? Arhiiv mäletab iseennast, kui keegi viitsib lugeda.")
        elif n == self.cases // 2:
            self.liis.append("Pool tehtud. Kell on kolm läbi, mina magaksin. Sina vist ei maga.")
        left = [c for c in self.case_list if c["file"] not in self.fixed]
        if len(left) == 1 and left[0].get("trip"):
            self.liis.append("Jäänud on üks protokoll, mille tekst on loetamatu. Ükski teine fail ei tea, mis seal seisis.")
            self.liis.append("Aga sina oled seal sees. Äkki saad sa minna… kirje sisse? Ava see ja vaata.")
        if not left:
            self.liis.append(f"Kõik {self.cases} on korras. Väljas läheb valgeks ja näitus avatakse kell kümme.")
            self.liis.append("Tule vaata, kuhu sinu sildid jõudsid.")

    # ---------------------------------------------------------------- the museum epilogue

    def held(self, wing=None):
        return []

    def restored_in(self, wing):
        return sum(1 for rid in self.restored if self.by_id[rid]["wing"] == wing)

    # ---------------------------------------------------------------- running

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
