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


class Archive(Scene):
    music = "archive"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        data = self.content.game["map"]
        self.world = game.world("archive", data)
        self.player = Player(self.state.archive_pos or data["start"])
        self.shelves = {s["id"]: s for s in self.content.shelves}
        self.cases = [p for p in self.world.props if p.data.get("shelf")]
        self.door = self.world.by_id["exit"]
        self.exit = pygame.Rect(data["exit"])                 # the way through the door once it is open
        self.door_images = [paint.make({**self.door.data, "open": state}).convert_alpha() for state in (False, True)]
        self.robot_img = assets.optional("tegelased/robot.png") or paint.robot()
        self.robot_guard, self.robot_aside = data["robot"]["guard"], data["robot"]["aside"]       # feet positions
        self.robot_pos = pygame.Vector2(self.robot_aside if self.door_open else self.robot_guard)
        self.dialogue = ui.DialogueBox()
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
        assets.play("unlock.ogg", 0.5)

    def robot_rect(self):
        rect = pygame.Rect(0, 0, 12, 5)
        rect.midbottom = (round(self.robot_pos.x), round(self.robot_pos.y))
        return rect

    def walkable(self, feet):
        if feet.colliderect(self.robot_rect()):
            return False
        return self.world.walkable(feet) or (self.door_open and self.exit.contains(feet))

    def unsolved(self, shelf_id):
        return [d for d in self.content.shelf_documents(self.shelves[shelf_id]) if d["id"] not in self.state.solved]

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        self.robot_pos.move_towards_ip(self.robot_aside if self.door_open else self.robot_guard, 26 * dt)
        if self.dialogue.update(dt, events) or self.leaving:
            self.player.update(dt, self.walkable, control=False)
            return
        self.player.update(dt, self.walkable)
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
        self.draw(self.game.screen)        # a clean picture for the reader to sit on
        self.scenes.push(Reader(self.game, shelf))

    def talk_to_robot(self):
        robot = self.content.game["robot"]
        lines = robot["after"] if self.door_open else robot["blocked"]
        self.dialogue.say([l.format(done=len(self.state.solved), total=self.state.total) for l in lines], robot["name"])

    # ---------------------------------------------------------------- drawing

    def draw(self, screen):
        world = self.world
        world.look_at(self.player.pos)
        self.door.image = self.door_images[self.door_open]
        pulse = 0.5 + 0.5 * math.sin(self.t * 3)
        glowing = [p for p in self.cases if self.unsolved(p.data["shelf"])]
        lights = [(round(self.player.pos.x), round(self.player.pos.y) - 12, 50, GHOST_LIGHT)]
        lights += [(p.rect.centerx, p.rect.centery, 44, tuple(int(c * (0.35 + 0.4 * pulse)) for c in settings.TEAL))
                   for p in glowing]
        outlines = [(p.rect, tuple(int(c * (0.5 + 0.5 * pulse)) for c in settings.TEAL)) for p in glowing]
        if self.near and not self.dialogue.active:
            outlines.append((self.near.rect, settings.CREAM))
        robot = self.robot_img
        actors = [self.player.actor(), (self.robot_pos.y, robot, (round(self.robot_pos.x) - robot.get_width() // 2,
                                                                 round(self.robot_pos.y) - robot.get_height()))]
        world.draw(screen, actors, lights, outlines)

        ui.draw_text(screen, f"records restored  {len(self.state.solved)} / {self.state.total}", (40, 24), "mono", 26,
                     settings.DIM)
        if self.dialogue.active:
            self.dialogue.draw(screen)
            return
        if glowing:
            target = min(glowing, key=lambda p: self.player.pos.distance_to(p.rect.center))
            ui.pointer(screen, world.to_screen(target.rect.center))
        elif self.door_open:
            ui.pointer(screen, world.to_screen(self.exit.center), settings.WARM)
        if self.near_robot:
            ui.key_prompt(screen, world.to_screen((self.robot_pos.x, self.robot_pos.y - robot.get_height())))
            ui.hint(screen, "E — talk")
        elif self.near:
            shelf = self.shelves[self.near.data["shelf"]]
            ui.key_prompt(screen, world.to_screen(self.near.rect.midtop))
            label = shelf["label"] + ("  ·  a memory is caught here" if self.unsolved(shelf["id"]) else "")
            ui.panel(screen, (settings.W / 2 - 400, 8, 800, 62))
            ui.draw_text(screen, label, (settings.W / 2, 39), "bold", 36, settings.CREAM, center=True)
            ui.hint(screen, "E — read this shelf")
