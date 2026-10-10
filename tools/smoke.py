"""Plays the whole game headlessly and saves screenshots to the given folder.

venv/bin/python tools/smoke.py /some/folder
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame

from game import core, layout
from game.app import Game
from game.card import Card
from game.world import World

out = sys.argv[1]
pygame.init()
screen = pygame.display.set_mode((core.W, core.H))
game = Game(screen)
DT = 1 / 60


def run(seconds, events=()):
    game.update(DT, list(events))
    for _ in range(int(seconds * 60)):
        game.update(DT, [])
    game.draw()


def shot(name):
    game.draw()
    pygame.image.save(screen, f"{out}/{name}.png")


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def teleport(pos):
    w = game.scene
    assert w.walkable(pygame.Vector2(pos)), f"not walkable: {pos}"
    w.ghost.pos.update(pos)
    w.ghost.vel.update(0, 0)
    w.cam = w.cam_target()


run(1.5)
shot("01_title")
run(1.5, [key(pygame.K_SPACE)])
assert isinstance(game.scene, World)
run(0.5)
shot("02_lobby")
# every spot and plinth must be reachable once its wing is open
for wing, room in layout.ROOMS.items():
    r = pygame.Rect(room)
    for p in layout.SPOTS.get(wing, []) + [(x, y + 70) for x, y in layout.PLINTHS.get(wing, [])]:
        assert r.collidepoint(p), (wing, p)

n = 0
for wing in ("linn", "vald", "hoim"):
    assert wing in game.unlocked, (wing, len(game.restored))
    teleport(pygame.Rect(layout.ROOMS[wing]).center)
    run(0.6)
    shot(f"1{n}_{wing}_enter")
    for hs in list(game.scene.wisps):
        if hs.data["wing"] == wing:
            teleport(hs.pos)
            run(1.0)
    assert len(game.held(wing)) == 12, len(game.held(wing))
    shot(f"1{n}_{wing}_gathered")
    for rec in [r for r in game.records if r["wing"] == wing]:
        plinth = next(h for h in game.scene.plinths if h.data is rec)
        teleport(plinth.pos)
        run(2.2)
        assert isinstance(game.scene, Card), game.scene
        card = game.scene
        if rec is game.records[0] or rec["id"] == "koiola":
            shot(f"1{n}_card_{rec['id']}")
            wrong = next(c for c in card.chips() if c[0]["rid"] != rec["id"])
            card.choose(*wrong)
            run(0.1)
            shot(f"1{n}_card_{rec['id']}_wrong")
            run(2.5)
        while card.reveal is None:
            good = next(c for c in card.chips() if c[0]["rid"] == rec["id"] and c[0]["idx"] == card.active)
            card.choose(*good)
            run(0.6)
        run(3.6)
        if rec["id"] in ("tubakavabrik", "koiola", "ankur"):
            shot(f"1{n}_restored_{rec['id']}")
        run(1.5, [key(pygame.K_SPACE)])
        assert isinstance(game.scene, World) and rec["id"] in game.restored
        run(1.0)
    shot(f"1{n}_{wing}_done")
    n += 1
teleport(layout.ENTRANCE)
run(3)
assert game.scene.ending is not None
run(8)
shot("30_ending")
run(14)
shot("31_credits")
run(1, [key(pygame.K_SPACE)])
assert not game.restored
print("smoke test passed; glow cache", len(core._glows), "text cache", len(core._texts))
