"""The archive: dim rooms of shelves that the ghost wanders through while the robot
guards the way out.

The rooms are described in data/game.json under "map" (see game/world.py for how a
map is written): where the shelves stand ("shelf" names an entry in "shelves"),
the door, the robot's two positions and where the ghost wakes up.
"""
import math

import pygame

from .. import assets, paint, settings, ui
from ..player import Player
from ..scene import Scene

GHOST_LIGHT = (150, 176, 190)
ROBOT_SPEED = 26          # art pixels per second
PULSE_STEPS = 10          # the shelves' glow breathes in this many shades
LEARNT = 90               # art pixels walked before the "how to move" line goes away


class Archive(Scene):
    music = "archive"
    pausable = True

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        data = self.content.game["map"]
        self.world = game.world("archive", data)
        self.player = Player(self.state.archive_pos or data["start"])
        self.world.look_at(self.player.pos)
        self.shelves = {s["id"]: s for s in self.content.shelves}
        self.cases = [p for p in self.world.props if p.data.get("shelf")]
        self.door = self.world.by_id["exit"]
        self.exit = pygame.Rect(data["exit"])                 # the way through the door once it is open
        self.door_images = [paint.make({**self.door.data, "open": state}).convert_alpha() for state in (False, True)]
        self.robot_img = assets.optional("tegelased/robot.png") or paint.robot()
        self.robot_guard, self.robot_aside = data["robot"]["guard"], data["robot"]["aside"]       # feet positions
        self.robot_pos = pygame.Vector2(self.robot_aside if self.door_open else self.robot_guard)
        self.dialogue = ui.DialogueBox(prompt=self.text("advance"))
        self.near = None           # the bookcase the ghost is standing at
        self.near_robot = False
        self.leaving = False

    def enter(self):
        robot = self.content.game["robot"]
        if self.state.first_time("welcome"):
            self.dialogue.say(robot["welcome"], robot["name"])
        elif self.state.all_solved and self.state.first_time("all_done"):
            self.dialogue.say(robot["done"], robot["name"], on_done=self.open_door)

    # ---------------------------------------------------------------- rules

    @property
    def door_open(self):
        return "door_open" in self.state.seen

    def open_door(self):
        self.state.seen.add("door_open")
        assets.play("door.ogg", 0.7)

    def robot_rect(self, pos=None):
        pos = self.robot_pos if pos is None else pos
        rect = pygame.Rect(0, 0, 12, 5)
        rect.midbottom = (round(pos.x), round(pos.y))
        return rect

    def move_robot(self, dt):
        """The robot walks between its post at the door and its place beside it. It waits
        rather than walk into the ghost, which could never get out from under it again."""
        step = self.robot_pos.move_towards(self.robot_aside if self.door_open else self.robot_guard, ROBOT_SPEED * dt)
        if not self.robot_rect(step).colliderect(self.player.feet()):
            self.robot_pos = step

    def walkable(self, feet):
        if feet.colliderect(self.robot_rect()):
            return False
        return self.world.walkable(feet) or (self.door_open and self.exit.contains(feet))

    def unsolved(self, shelf_id):
        return [d for d in self.content.shelf_documents(self.shelves[shelf_id]) if d["id"] not in self.state.solved]

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        self.move_robot(dt)
        busy = self.dialogue.update(dt, events) or self.leaving
        before = pygame.Vector2(self.player.pos)
        self.player.update(dt, self.walkable, control=not busy)
        self.world.look_at(self.player.pos, dt)
        if busy:
            return
        self.state.walked += self.player.pos.distance_to(before)
        feet = self.player.feet()
        self.near = self.world.nearest(feet, self.cases)
        self.near_robot = self.robot_rect().inflate(18, 18).colliderect(feet)

        if feet.bottom < self.exit.top + 10:
            self.leaving = True
            from .ending import Ending
            self.scenes.go(lambda: Ending(self.game))
        elif ui.confirm(events):
            if self.near_robot:
                self.talk_to_robot()
            elif self.near:
                self.open_shelf(self.shelves[self.near.data["shelf"]])

    def open_shelf(self, shelf):
        from .reader import Reader
        self.state.archive_pos = tuple(self.player.pos)
        self.near = None
        assets.play("place.ogg", 0.5)
        self.scenes.push(Reader(self.game, shelf))

    def talk_to_robot(self):
        robot = self.content.game["robot"]
        lines = robot["after"] if self.door_open else robot["blocked"]
        self.dialogue.say([l.format(done=len(self.state.solved), total=self.state.total) for l in lines], robot["name"])

    # ---------------------------------------------------------------- drawing

    def draw(self, screen):
        world = self.world
        self.door.image = self.door_images[self.door_open]
        for case in self.cases:
            case.open(case is self.near and not self.dialogue.active)
        # a few fixed shades instead of a new one every frame: each shade of light is a picture that is kept
        pulse = round((0.5 + 0.5 * math.sin(self.t * 3)) * PULSE_STEPS) / PULSE_STEPS
        glowing = [p for p in self.cases if self.unsolved(p.data["shelf"])]
        lights = [(round(self.player.pos.x), round(self.player.pos.y) - 12, 50, GHOST_LIGHT)]
        lights += [(p.rect.centerx, p.rect.centery, 44, tuple(int(c * (0.35 + 0.4 * pulse)) for c in settings.TEAL))
                   for p in glowing]
        outlines = [(p.rect, tuple(int(c * (0.5 + 0.5 * pulse)) for c in settings.TEAL)) for p in glowing]
        if self.near and not self.dialogue.active:
            outlines.append((self.near.rect, settings.CREAM))
        robot = self.robot_img
        robot_at = (round(self.robot_pos.x) - robot.get_width() // 2, round(self.robot_pos.y) - robot.get_height())
        world.draw(screen, self.player, [(self.robot_pos.y, robot, robot_at)], lights, outlines)

        ui.draw_text(screen, self.text("archive.count", done=len(self.state.solved), total=self.state.total), (40, 24),
                     "pixel", 26, settings.DIM)
        if self.dialogue.active:
            self.dialogue.draw(screen)
        elif not self.plain:
            self.draw_prompts(screen, glowing)

    def draw_prompts(self, screen, glowing):
        """Where to go (an arrow to the nearest shelf that still glows, or to the open door)
        and what can be done right here."""
        world = self.world
        if glowing:
            target = min(glowing, key=lambda p: self.player.pos.distance_to(p.rect.center))
            ui.pointer(screen, world.to_screen(target.rect.center))
        elif self.door_open:
            ui.pointer(screen, world.to_screen(self.exit.center), settings.WARM)
        if self.near_robot:
            ui.key_prompt(screen, world.to_screen((self.robot_pos.x, self.robot_pos.y - self.robot_img.get_height())))
            self.hint(screen, "archive.talk")
        elif self.near:
            shelf = self.shelves[self.near.data["shelf"]]
            ui.key_prompt(screen, world.to_screen(self.near.rect.midtop))
            name = shelf["label"] + (f"  ·  {self.text('archive.caught')}" if self.unsolved(shelf["id"]) else "")
            ui.panel(screen, (settings.W / 2 - 400, settings.H - 130, 800, 62))
            ui.draw_text(screen, name, (settings.W / 2, settings.H - 99), "pixel", 40, settings.CREAM, center=True)
            self.hint(screen, "archive.read")
        elif self.state.walked < LEARNT:
            self.hint(screen, "archive.move")
