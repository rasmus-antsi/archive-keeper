"""Plays the whole game headlessly and saves a screenshot of every scene.

venv/bin/python tools/smoke.py /some/folder
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame

from game import settings
from game.app import Game
from game.display import Display
from game.scenes.archive import Archive
from game.scenes.inside import Inside
from game.scenes.ending import Ending
from game.scenes.intro import Intro
from game.scenes.memory import Memory
from game.scenes.menu import Menu
from game.scenes.reader import Reader

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
pygame.init()
display = Display()
game = Game(display)
screen = display.surface
DT = 1 / 60
SPACE = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)


def run(seconds=0.0, *events):
    game.update(DT, list(events))
    for _ in range(int(seconds * 60)):
        game.update(DT, [])
    game.draw()


def shot(name):
    game.draw()
    pygame.image.save(screen, f"{out}/{name}.png")


def click(pos):
    """A left click at a game position, sent through the window so the mapping is tested too."""
    win = (display.view.x + pos[0] * display.view.w / settings.W, display.view.y + pos[1] * display.view.h / settings.H)
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=win)


def stand_at(scene, rect):
    """Put the ghost just below a thing, close enough to press E at it."""
    rect = pygame.Rect(rect)
    scene.player.pos.update(rect.centerx, rect.bottom + 6)
    run(0.1)


def top(kind):
    assert isinstance(game.scenes.top, kind), f"expected {kind.__name__}, got {type(game.scenes.top).__name__}"
    return game.scenes.top


def talk_through():
    """Press space until the top scene's dialogue is finished."""
    for _ in range(60):
        if not game.scenes.top.dialogue.active:
            return
        run(0.05, SPACE)
    raise AssertionError("dialogue never ended")


for _ in range(400):         # the loading bar
    if isinstance(game.scenes.top, Menu) and game.scenes.fade == 0:
        break
    run()
top(Menu)
run(1)
shot("1-menu")
run(1, SPACE)
top(Intro)
run(6)
shot("2-intro")
run(0.1, SPACE)          # show all the text
shot("2-intro-full")
run(1, SPACE)

room = top(Archive)
run(1)
shot("3-archive-welcome")
talk_through()
for case in room.cases:                 # every bookcase opens and shows its records
    stand_at(room, case.solid)
    assert room.near is case, f"not standing at a {case.data['shelf']} bookcase"
    shot(f"4-at-shelf-{case.data['shelf']}-{case.rect.x}")
    run(0.2, SPACE)
    reader = top(Reader)
    assert reader.entries, f"shelf {case.data['shelf']} is empty"
    run(0.1, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    shot(f"5-reader-{case.data['shelf']}")
    run(0.2, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    top(Archive)

room.player.pos.update(170, 150)
run(0.2)
shot("4-archive-hall")
room.player.pos.update(350, 170)
run(0.2)
shot("4-archive-stacks")
room.player.pos.update(room.robot_guard[0], room.robot_guard[1] + 10)        # the robot will not let the ghost through
run(0.2)
run(0.3, SPACE)
shot("6-robot-blocks")
talk_through()


def fetch(memory, item):
    """Find the thing, take it out of whatever holds it and carry it to whoever asked."""
    holder = memory.world.by_id[memory.where[item]]
    stand_at(memory, holder.solid)
    assert memory.near is holder, f"not standing at {holder.id}"
    shot(f"8-memory-at-{holder.id}")
    run(0.2, SPACE)
    inside = top(Inside)
    inside.cursor = next(i for i, it in enumerate(inside.items) if it["id"] == item)
    shot(f"8-memory-inside-{holder.id}")
    run(0.2, SPACE)
    top(Memory)
    assert memory.carrying == item
    stand_at(memory, memory.npcs[0].solid)
    shot(f"8-memory-carrying-{item}")
    run(1.0, SPACE)


for doc in game.content.documents:      # solve every memory, with one wrong guess each
    room = top(Archive)
    case = next(c for c in room.cases if c.data["shelf"] == doc["shelf"])
    stand_at(room, case.solid)
    run(0.2, SPACE)
    reader = top(Reader)
    reader.cursor = next(i for i, e in enumerate(reader.entries) if e["doc"] is doc)
    run(0.1)
    shot(f"7-reader-memory-{doc['id']}")
    run(1.0, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    shot(f"7-spiral-{doc['id']}")
    run(1.2)
    memory = top(Memory)
    shot(f"8-memory-{doc['id']}-hint")
    for room in memory.world.rooms:        # every house from the street, roof on
        if room.roof:
            memory.player.pos.update(room.rect.centerx, room.rect.bottom + 14)
            run(0.5)
            shot(f"8-memory-house-{room.data['id']}")
    memory.player.pos.update(doc["map"]["start"])
    for i, request in enumerate(doc["requests"]):
        talk_through()
        shot(f"8-memory-{doc['id']}-{i}-look")
        fetch(memory, next(item for item in memory.where if item != request["target"]))
        assert memory.request == i and memory.dialogue.active, "a wrong thing should repeat the hint"
        talk_through()
        fetch(memory, request["target"])
        assert memory.request == i + 1, "the right thing should move on"
    talk_through()
    run(1.5)
    assert doc["id"] in game.state.solved

room = top(Archive)
shot("9-archive-all-done")
talk_through()
run(2)
assert "door_open" in game.state.seen
shot("9-door-open")
room.player.pos.update(room.exit.centerx, room.exit.top + 8)
run(1.5)
top(Ending)
shot("10-ending")
run(2)
run(1.5, SPACE)
top(Menu)
print("smoke test passed:", len(os.listdir(out)), "screenshots")
