"""Plays the whole game headlessly, checks it on the way and saves a screenshot of every scene.

venv/bin/python tools/smoke.py /some/folder
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame

from game import assets, content, player, settings
from game.app import Game
from game.display import Display
from game.scenes import boot
from game.scenes.archive import Archive, LEARNT
from game.scenes.ending import Ending
from game.scenes.found import Found
from game.scenes.inside import Inside
from game.scenes.intro import Intro
from game.scenes.memory import Memory
from game.scenes.pause import Credits, Pause, Settings
from game.scenes.reader import Reader
from game.scenes.title import Title

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

held = set()                    # the keys the test is holding down
pygame.key.get_pressed = lambda: type("Keys", (), {"__getitem__": lambda self, key: key in held})()

missing = []                    # interface text that is asked for but not in data/game.json
_text = content.Content.text


def _checked_text(self, key, **values):
    line = _text(self, key, **values)
    if line == f"[{key}]":
        missing.append(key)
    return line


content.Content.text = _checked_text

pygame.init()
display = Display()
game = Game(display)
screen = display.surface
DT = 1 / 60


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


SPACE, ENTER, ESC = key(pygame.K_SPACE), key(pygame.K_RETURN), key(pygame.K_ESCAPE)
UP, DOWN, LEFT, RIGHT = key(pygame.K_UP), key(pygame.K_DOWN), key(pygame.K_LEFT), key(pygame.K_RIGHT)


def run(seconds=0.0, *events):
    game.update(DT, list(events))
    for _ in range(int(seconds * 60)):
        game.update(DT, [])
    game.draw()


def shot(name):
    game.draw()
    pygame.image.save(screen, f"{out}/{name}.png")


def window(pos):
    """A game position as the window position the mouse would report, so the mapping is tested too."""
    return display.view.x + pos[0] * display.view.w / settings.W, display.view.y + pos[1] * display.view.h / settings.H


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=window(pos))


def point(pos):
    return pygame.event.Event(pygame.MOUSEMOTION, pos=window(pos), rel=(0, 0), buttons=(0, 0, 0))


def wheel(y):
    return pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=y, precise_x=0.0, precise_y=float(y))


def stand_at(scene, rect):
    """Put the ghost just below a thing, close enough to press E at it."""
    rect = pygame.Rect(rect)
    scene.player.pos.update(rect.centerx, rect.bottom + 6)
    scene.player.vel.update(0, 0)
    run(0.1)


def top(kind):
    assert isinstance(game.scenes.top, kind), f"expected {kind.__name__}, got {type(game.scenes.top).__name__}"
    return game.scenes.top


def talk_through():
    """Press space until the top scene's dialogue is finished."""
    for _ in range(80):
        if not game.scenes.top.dialogue.active:
            return
        run(0.05, SPACE)
    raise AssertionError("dialogue never ended")


def walk(seconds, *keys):
    """Hold keys down for a while; returns the camera position after every frame."""
    held.update(keys)
    cameras = []
    for _ in range(int(seconds * 60)):
        game.update(DT, [])
        cameras.append(game.scenes.top.world.origin)
    held.difference_update(keys)
    run(0.3)
    return cameras


# ---------------------------------------------------------------- loading and the title screen

frames = 0
while not (isinstance(game.scenes.top, Title) and game.scenes.fade == 0):
    run()
    frames += 1
    assert frames < 400, "the loading screen never ended"
    if frames == 3:
        shot("0-loading")
print(f"loaded in {frames} frames")
title = top(Title)
run(1.5)
assert assets._playing == "menu" and assets._fade == 1, "the title music should have faded in"
shot("1-title")
run(0.1, key(pygame.K_m))
run(0.1)
assert assets.muted and assets._heard == 0, "M should silence everything"
run(0.1, key(pygame.K_m))
run(0.1, DOWN)
assert title.menu.cursor == 1, "down should move to the second choice"
run(0.1, UP, UP)
assert title.menu.cursor == len(title.menu.choices) - 1, "up from the first choice should wrap to the last"
run(0.1, DOWN, DOWN)
run(0.3, ENTER)
tuning = top(Settings)
shot("1-settings")
before = assets.levels["music"]
run(0.1, LEFT, LEFT)
assert abs(assets.levels["music"] - (before - 0.2)) < 0.001, "left should turn the music down"
run(0.1, click((tuning.menu.bar(0).right - 4, tuning.menu.bar(0).centery)))
assert assets.levels["music"] == 1.0, "a click at the end of the bar should turn it right up"
run(0.1, DOWN, LEFT)
assert assets.levels["sound"] == 0.9
run(0.1, RIGHT)
run(0.3, ESC)
top(Title)
run(0.1, point(title.menu.row(2).center))
assert title.menu.cursor == 2, "pointing at a choice should select it"
run(0.3, click(title.menu.row(2).center))
top(Credits)
shot("1-credits")
run(0.3, SPACE)
top(Title)
run(1, click(title.menu.row(0).center))

# ---------------------------------------------------------------- the opening message

intro = top(Intro)
while not intro.typed():
    run(0.1)
shot("2-intro")
run(0.5, SPACE)
assert intro.page == 1 and not intro.typed(), "space should bring the next paragraph"
shot("2-intro-typing")
run(0.1, SPACE)          # the rest of the paragraph at once
assert intro.page == 1 and intro.typed(), "a press while it types should only finish the paragraph"
for _ in range(2 * len(intro.paragraphs)):
    run(0.1, SPACE)
    if intro.last and intro.typed():
        break
shot("2-intro-last")
run(1, SPACE)

# ---------------------------------------------------------------- the archive

room = top(Archive)
run(1)
assert assets._playing == "archive", "the archive has its own music"
shot("3-archive-welcome")
talk_through()
shot("3-archive-first-steps")
loud = assets._heard
run(0.5, ESC)
top(Pause)
assert assets._heard < loud * 0.6, "the music should be held down behind the pause menu"
shot("3-pause")
run(0.2, DOWN)
run(0.3, ENTER)
top(Settings)
run(0.3, ESC)
top(Pause)
run(0.3, ESC)
top(Archive)

start = room.player.pos.x
cameras = walk(2.0, pygame.K_d)
moved = room.player.pos.x - start
assert abs(moved - player.SPEED * 2) < 8, f"two seconds of walking should cover {player.SPEED * 2} pixels, not {moved:.1f}"
assert game.state.walked > LEARNT
steps = [b[0] - a[0] for a, b in zip(cameras[-40:], cameras[-39:])]
assert min(steps) >= 7 and max(steps) <= 10, f"the camera should scroll evenly, a screen pixel at a time: {steps}"
shot("3-archive-walked")

for case in room.cases:                 # every bookcase opens and shows its records
    stand_at(room, case.solid)
    assert room.near is case, f"not standing at a {case.data['shelf']} bookcase"
    shot(f"4-at-shelf-{case.data['shelf']}-{case.rect.x}")
    run(0.3, SPACE)
    reader = top(Reader)
    assert reader.entries, f"shelf {case.data['shelf']} is empty"
    run(0.3, DOWN)
    shot(f"5-reader-{case.data['shelf']}")
    was = reader.cursor
    run(0.1, wheel(-3))
    assert reader.cursor == min(was + 3, len(reader.entries) - 1), "the wheel should move three records down"
    run(0.1, key(pygame.K_END))
    assert reader.cursor == len(reader.entries) - 1
    run(0.1, key(pygame.K_HOME))
    assert reader.cursor == 0
    run(0.1, click(reader.row_rect(2).center))
    assert reader.cursor == 2, "a click should pick that record"
    run(0.3, ESC)
    top(Archive)

room.player.pos.update(170, 150)
run(0.2)
shot("4-archive-hall")
room.player.pos.update(400, 172)
run(0.2)
shot("4-archive-stacks")
sofa = next(p for p in room.world.props if p.type == "sofa")       # the ghost half hidden behind furniture
room.player.pos.update(sofa.rect.centerx + 3.4, sofa.rect.top + 9.6)
run(0.2)
shot("4-archive-behind-sofa")
room.player.pos.update(room.robot_guard[0], room.robot_guard[1] + 10)        # the robot will not let the ghost through
run(0.2)
run(0.3, SPACE)
shot("6-robot-blocks")
talk_through()


# ---------------------------------------------------------------- the memories

def fetch(memory, item):
    """Find the thing, take it out of whatever holds it and carry it to whoever asked."""
    holder = memory.world.by_id[memory.where[item]]
    stand_at(memory, holder.solid)
    assert memory.near is holder, f"not standing at {holder.id}"
    shot(f"8-memory-at-{holder.id}")
    run(0.3, SPACE)
    inside = top(Inside)
    inside.cursor = next(i for i, it in enumerate(inside.items) if it["id"] == item)
    shot(f"8-memory-inside-{holder.id}")
    run(0.3, SPACE)
    top(Memory)
    assert memory.carrying == item
    stand_at(memory, memory.npcs[0].solid)
    shot(f"8-memory-carrying-{item}")
    run(0.3, SPACE)


def step_into(doc):
    room = top(Archive)
    case = next(c for c in room.cases if c.data["shelf"] == doc["shelf"])
    stand_at(room, case.solid)
    run(0.3, SPACE)
    reader = top(Reader)
    reader.cursor = next(i for i, e in enumerate(reader.entries) if e["doc"] is doc)
    run(0.1)
    shot(f"7-reader-memory-{doc['id']}")
    run(1.0, ENTER)
    shot(f"7-spiral-{doc['id']}")
    run(1.2)
    return top(Memory)


for doc in game.content.documents:      # solve every memory, with one wrong guess each
    memory = step_into(doc)
    shot(f"8-memory-{doc['id']}-hint")
    talk_through()

    run(0.3, ESC)                       # giving up from the pause menu leads back to the archive, nothing solved
    pause = top(Pause)
    shot(f"8-memory-{doc['id']}-pause")
    run(0.2, DOWN, DOWN)
    run(3, ENTER)
    top(Archive)
    assert doc["id"] not in game.state.solved
    memory = step_into(doc)
    talk_through()

    for house in memory.world.rooms:        # every house from the street, roof on
        if house.roof:
            memory.player.pos.update(house.rect.centerx, house.rect.bottom + 14)
            run(0.5)
            shot(f"8-memory-house-{house.data['id']}")
    for door in memory.world.doors:         # walking at the edge of a doorway slips through it
        memory.player.pos.update(door.left + 1, door.bottom + 8)
        memory.player.vel.update(0, 0)
        walk(1.0, pygame.K_w)
        assert memory.player.pos.y < door.top, f"the ghost should have slipped in through the door at {tuple(door)}"
    empty = next((p for p in memory.containers if not p.data["holds"]), None)
    if empty:
        stand_at(memory, empty.solid)
        run(0.3, SPACE)
        assert not top(Inside).items
        shot("8-memory-inside-empty")
        run(0.3, SPACE)
        top(Memory)
    memory.player.pos.update(doc["map"]["start"])
    for i, request in enumerate(doc["requests"]):
        talk_through()
        shot(f"8-memory-{doc['id']}-{i}-look")
        fetch(memory, next(item for item in memory.where if item != request["target"]))
        assert memory.request == i and memory.dialogue.active, "a wrong thing should repeat the hint"
        talk_through()
        fetch(memory, request["target"])
        assert memory.request == i + 1, "the right thing should move on"
        found = top(Found)                  # the thing goes back onto its page
        assert not found.settled
        shot(f"8-memory-{doc['id']}-{i}-found-falling")
        run(0.1, SPACE)
        assert found.settled, "a press should skip to the finished page"
        shot(f"8-memory-{doc['id']}-{i}-found")
        run(0.5, SPACE)
        top(Memory)
    talk_through()
    run(1.5)
    assert doc["id"] in game.state.solved

# ---------------------------------------------------------------- the way out

room = top(Archive)
shot("9-archive-all-done")
room.player.pos.update(room.robot_aside[0], room.robot_aside[1])       # stand right where the robot wants to go
talk_through()
run(3)
assert "door_open" in game.state.seen
assert not room.robot_rect().colliderect(room.player.feet()), "the robot walked into the ghost"
before = pygame.Vector2(room.player.pos)
walk(0.5, pygame.K_d)
assert room.player.pos.distance_to(before) > 10, "the ghost is stuck under the robot"
run(3)
assert room.robot_pos.distance_to(room.robot_aside) < 1, "the robot should reach its place once the ghost is out of the way"
shot("9-door-open")
room.player.pos.update(room.exit.centerx - 3, room.exit.bottom + 12)       # on the floor below the door, a little to one side
room.player.vel.update(0, 0)
held.add(pygame.K_w)                    # and out on foot: placing the ghost in the doorway once hid a door nobody could enter
run(1.5)
held.discard(pygame.K_w)
top(Ending)
shot("10-ending-start")
run(4)
shot("10-ending")
run(1.5, SPACE)
top(Title)

run(1, ENTER)                           # a second game starts from nothing
top(Intro)
run(1, ESC)                             # Esc skips the whole message
room = top(Archive)
assert not game.state.solved and room.dialogue.active and not room.door_open, "a new game should start afresh"

# ---------------------------------------------------------------- loose ends

unloaded = sorted(set(assets._fonts) - set(boot.FONTS))
assert not unloaded, f"add these to FONTS in game/scenes/boot.py so they load behind the bar: {unloaded}"
assert not missing, f"interface text missing from data/game.json: {sorted(set(missing))}"
print("smoke test passed:", len(os.listdir(out)), "screenshots")
