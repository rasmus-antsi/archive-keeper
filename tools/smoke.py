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
from game.scenes.archive import Archive
from game.scenes.ending import Ending
from game.scenes.intro import Intro
from game.scenes.memory import Memory
from game.scenes.menu import Menu
from game.scenes.reader import Reader

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
pygame.init()
screen = pygame.display.set_mode((settings.W, settings.H))
game = Game(screen)
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


def click(canvas_pos):
    pos = (canvas_pos[0] * settings.SCALE, canvas_pos[1] * settings.SCALE)
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


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
for shelf in game.content.shelves:      # every shelf opens and shows its records
    rect = pygame.Rect(shelf["rect"])
    room.player.pos.update(max(34, min(286, rect.centerx)), max(68, min(200, rect.centery)))
    if rect.width > rect.height:
        room.player.pos.y = 66
    else:
        room.player.pos.x = 30 if rect.x < 100 else 290
    run(0.2)
    assert room.near is shelf, f"not standing at shelf {shelf['id']}"
    shot(f"4-at-shelf-{shelf['id']}")
    run(0.2, SPACE)
    reader = top(Reader)
    assert reader.entries, f"shelf {shelf['id']} is empty"
    run(0.1, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    shot(f"5-reader-{shelf['id']}")
    run(0.2, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    top(Archive)

room.player.pos.update(160, 190)        # the robot will not let the ghost through
run(0.2)
run(0.3, SPACE)
shot("6-robot-blocks")
talk_through()

for doc in game.content.documents:      # solve every memory, with one wrong guess each
    shelf = next(s for s in game.content.shelves if s["id"] == doc["shelf"])
    room = top(Archive)
    room.player.pos.update(pygame.Rect(shelf["rect"]).centerx, 66)
    run(0.2)
    run(0.2, SPACE)
    reader = top(Reader)
    reader.cursor = next(i for i, e in enumerate(reader.entries) if e["doc"] is doc)
    run(0.1)
    shot(f"7-reader-memory-{doc['id']}")
    run(1.5, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    memory = top(Memory)
    shot(f"8-memory-{doc['id']}-hint")
    for i, request in enumerate(doc["requests"]):
        talk_through()
        shot(f"8-memory-{doc['id']}-{i}-look")
        wrong = next(o for o in doc["objects"] if o["id"] != request["target"])
        run(1.0, click(pygame.Rect(wrong["rect"]).center))
        assert memory.request == i and memory.dialogue.active, "a wrong guess should repeat the hint"
        shot(f"8-memory-{doc['id']}-{i}-wrong")
        talk_through()
        right = next(o for o in doc["objects"] if o["id"] == request["target"])
        run(0.3, click(pygame.Rect(right["rect"]).center))
        assert memory.request == i + 1, "the right object should move on"
    talk_through()
    run(1.5)
    assert doc["id"] in game.state.solved

room = top(Archive)
shot("9-archive-all-done")
talk_through()
run(2)
assert "door_open" in game.state.seen
shot("9-door-open")
room.player.pos.update(160, 222)
run(1.5)
top(Ending)
shot("10-ending")
run(2)
run(1.5, SPACE)
top(Menu)
print("smoke test passed:", ", ".join(sorted(os.listdir(out))))
