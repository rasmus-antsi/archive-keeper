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
from game.desk import Desk
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


def click(action_kind, match=lambda a: True):
    """Click the first hot area with this kind of action."""
    game.draw()
    desk = game.scene
    for rect, action in reversed(desk.hot):
        if action[0] == action_kind and match(action):
            desk.do(action)
            return
    raise AssertionError(f"nothing to click: {action_kind}")


def teleport(pos):
    s = game.scene
    assert s.walkable(pygame.Vector2(pos)), f"not walkable: {pos}"
    s.ghost.pos.update(pos)
    s.ghost.vel.update(0, 0)
    s.cam = s.cam_target()


SPACE = key(pygame.K_SPACE)

# every ordinary blank must be answerable from another file of the same batch
for case in game.case_list:
    f = game.file_by_id[case["file"]]
    for label in case.get("blanks", []):
        truth = dict(f["fields"])[label]
        assert truth, (f["id"], label)
        others = [o for o in game.files if o is not f and o["group"] == f["group"]
                  and not game.blank(o, label) and dict(o["fields"]).get(label) == truth]
        assert others, f"no sibling answers {f['id']} {label}"

run(1.5)
shot("01_title")
run(1.5, [SPACE])
desk = game.scene
assert isinstance(desk, Desk)
run(0.5)
shot("02_boot")
while game.liis:
    run(0.2, [SPACE])
shot("03_all_files")
click("folder", lambda a: a[1] == "!")
run(0.3)
shot("04_broken")

for n, case in enumerate(c for c in game.case_list if not c.get("trip")):
    f = game.file_by_id[case["file"]]
    for label in case["blanks"]:
        truth = dict(f["fields"])[label]
        desk.do(("find", "group", f["group"]))
        sibling = next(o for o in desk.listing() if o is not f and dict(o["fields"]).get(label) == truth and not game.blank(o, label))
        desk.do(("open", sibling))
        run(0.2)
        if n == 0:
            shot("05_sibling")
        click("copy", lambda a: a[1] == label)
        desk.do(("open", f))
        run(0.2)
        if n == 0:
            shot("06_broken_file")
            desk.do(("copy", "Rahvas", "vale vastus"))
            desk.do(("blank", label))
            click("paste", lambda a: a[1]["value"] == "vale vastus")
            run(0.1)
            shot("07_wrong")
            desk.do(("forget", game.clip[-1]))
        if desk.pick != label:
            desk.do(("blank", label))
        run(0.1)
        if n == 0:
            shot("08_pick")
        click("paste", lambda a: a[1]["value"] == truth)
        run(0.6)
    assert f["id"] in game.fixed, f["id"]
    if n == 0:
        shot("09_fixed")
    while game.liis:
        run(0.2, [SPACE])
    desk.do(("close",))

# the last one needs a trip
f = game.file_by_id["vk-119032"]
desk.do(("open", f))
run(0.3)
shot("10_trip_file")
click("trip")
run(1.5)
lv = game.scene
assert isinstance(lv, Level), lv
for _ in range(4):
    run(0.3, [SPACE])
teleport(lv.by_id["peremees_0"].pos + (0, 50))
run(9)
door = next(h for h in lv.haunts if h.id == "door")
teleport(door.pos)
run(1.6, [SPACE])
run(0.3, [SPACE])
shot("11_trip_box")
teleport((1300, 620))
run(24)
candle = next(h for h in lv.haunts if h.id == "candle")
teleport(candle.pos)
run(1.6, [SPACE])
run(0.3, [SPACE])
run(18)
assert lv.complete(), [x["state"] for x in lv.facts()]
shot("12_trip_done")
for _ in range(3):
    run(0.3, [SPACE])
teleport(lv.exit.pos)
run(2.5)
desk = game.scene
assert isinstance(desk, Desk) and desk.open is f, desk
shot("13_back")
for label in [l for fid, l in sorted(game.blanks) if fid == f["id"] and l != "__text"]:
    truth = dict(f["fields"])[label]
    desk.do(("blank", label))
    click("paste", lambda a: a[1]["value"] == truth)
    run(0.5)
assert len(game.fixed) == game.cases, game.fixed
run(0.5)
shot("14_text_back")
while game.liis:
    run(0.2, [SPACE])
desk.do(("close",))
run(0.3)
shot("15_all_done")
click("open_show")
run(2)
assert isinstance(game.scene, World), game.scene
shot("20_museum")
teleport(layout.ENTRANCE)
run(3)
assert game.scene.ending is not None
run(24)
shot("21_credits")
run(1, [SPACE])
assert not game.fixed and isinstance(game.scene.desk, Desk)
print("smoke test passed; glow cache", len(core._glows), "text cache", len(core._texts))
