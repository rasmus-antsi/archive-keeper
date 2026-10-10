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
from game.home import Home
from game.level import Level
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
    s = game.scene
    assert s.walkable(pygame.Vector2(pos)), f"not walkable: {pos}"
    s.ghost.pos.update(pos)
    s.ghost.vel.update(0, 0)
    s.cam = s.cam_target()


SPACE = key(pygame.K_SPACE)
run(1.5)
shot("01_title")
run(1.5, [SPACE])
assert isinstance(game.scene, Home)
run(3)
shot("02_home")
drawer = next(h for h in game.scene.drawers if h.data["id"] == "koiola")
teleport(drawer.pos)
run(0.3)
shot("03_home_drawer")
run(2)
assert isinstance(game.scene, Card), game.scene
shot("04_card_preview")
run(1.5, [SPACE])
assert isinstance(game.scene, Level), game.scene
lv = game.scene
run(1.0)
shot("10_arrive")

# every person and haunt must stand somewhere the ghost can reach
for n in lv.npcs:
    for st in n.states:
        near = [pygame.Vector2(st["pos"]) + d for d in ((0, 0), (0, 60), (0, -60), (60, 0), (-60, 0))]
        assert any(all(f in st.get("when", []) + ["door_open"] or True for f in ()) and
                   any(r.collidepoint(p) for r, _ in lv.walk) for p in near), (n.id, st["pos"])
for h in lv.haunts:
    assert any(r.collidepoint(h.pos) for r, _ in lv.walk), h.id

teleport(lv.by_id["peremees_0"].pos + (0, 50))
run(1.2)
shot("11_listen")
run(8)
assert lv.facts()[0]["state"] == "held", "name not overheard"
teleport(lv.by_id["tydruk"].pos + (60, 30))
run(1.5)
shot("12_girl")
teleport((1200, 500))            # inside, before the door opens
run(1.5)
shot("13_inside_quiet")
door = next(h for h in lv.haunts if h.id == "door")
teleport(door.pos)
run(0.3)
shot("14_door_prompt")
run(0.4, [SPACE])
shot("15_haunting")
run(1.0)
assert "door_open" in lv.flags
teleport((1300, 620))
run(7)
shot("16_row")
run(16)
assert "row_done" in lv.flags and lv.facts()[1]["state"] == "held"
candle = next(h for h in lv.haunts if h.id == "candle")
teleport(candle.pos)
run(1.5, [SPACE])
run(9)
shot("17_verdict")
run(8)
assert lv.complete(), [f["state"] for f in lv.facts()]
teleport(lv.exit.pos + (60, -40))
run(0.5)
shot("18_exit")
teleport(lv.exit.pos)
run(2.5)
assert isinstance(game.scene, Card), game.scene
card = game.scene
shot("20_card")
while card.reveal is None:
    good = next(c for c in card.chips() if c[0]["idx"] == card.active)
    card.choose(*good)
    run(0.6)
run(3.6)
shot("21_restored")
run(1.5, [SPACE])
assert isinstance(game.scene, Home) and "koiola" in game.restored
run(4)
shot("22_home_after")
teleport(game.scene.hatch.pos)
run(3)
assert isinstance(game.scene, World), game.scene
run(1)
shot("30_museum")
teleport(layout.ENTRANCE)
run(3)
assert game.scene.ending is not None
run(22)
shot("31_credits")
run(1, [SPACE])
assert not game.restored and isinstance(game.scene.home, Home)
print("smoke test passed; glow cache", len(core._glows), "text cache", len(core._texts))
