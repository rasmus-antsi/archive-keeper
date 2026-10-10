"""The archive room: the ghost walks between the shelves while the robot guards the door.

Painted art replaces the stand-ins as soon as the files exist:
  assets/img/taustad/arhiiv.png     the whole room, 1920x1080 (shelves, furniture and door included)
  assets/img/tegelased/robot.png    the robot
Where things are (floor, door, shelves, furniture that blocks the way) is in
data/game.json under "room" and "shelves"; move them there to match the painting.
"""
import math

import pygame

from .. import assets, settings, ui
from ..player import Player
from ..scene import Scene

ROBOT_FEET = (96, 42)
REACH = 60                     # how close to a shelf counts as standing at it


class Archive(Scene):
    music = "archive"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        room = self.content.game["room"]
        self.floor = pygame.Rect(room["floor"])
        self.door = pygame.Rect(room["door"])
        self.obstacles = [pygame.Rect(r) for r in room.get("obstacles", [])]
        self.robot_guard, self.robot_aside = room["robot_guard"], room["robot_aside"]    # feet positions
        self.rug = room.get("rug")
        self.player = Player(self.state.archive_pos or room["start"])
        self.shelves = [(s, pygame.Rect(s["rect"])) for s in self.content.shelves]
        self.background = assets.backdrop("taustad/arhiiv.png")
        self.stand_in = None       # (door_open, picture) painted when there is no background yet
        self.robot_img = assets.sprite("tegelased/robot.png") if assets.optional("tegelased/robot.png") \
            else assets.enlarge(_stand_in_robot(), settings.PIXEL)
        self.robot_pos = pygame.Vector2(self.robot_aside if "door_open" in self.state.seen else self.robot_guard)
        self.dialogue = ui.DialogueBox()
        self.near = None           # the shelf dict the ghost is standing at
        self.near_robot = False
        self.leaving = False

    def enter(self):
        robot = self.content.game["robot"]
        if self.state.first_time("welcome"):
            self.dialogue.say(robot["welcome"], robot["name"])
        elif self.state.all_solved and self.state.first_time("all_done"):
            self.dialogue.say(robot["done"], robot["name"], on_done=self.open_door)

    # ---------------------------------------------------------------- rules

    def open_door(self):
        self.state.seen.add("door_open")
        assets.play("unlock.ogg", 0.5)

    def robot_rect(self):
        rect = pygame.Rect((0, 0), ROBOT_FEET)
        rect.midbottom = (round(self.robot_pos.x), round(self.robot_pos.y))
        return rect

    def walkable(self, feet):
        if feet.colliderect(self.robot_rect()) or feet.collidelist(self.obstacles) >= 0:
            return False
        if self.floor.contains(feet):
            return True
        # through the doorway, once the robot has stepped aside
        return "door_open" in self.state.seen and self.door.left <= feet.left and feet.right <= self.door.right \
            and self.floor.top <= feet.top and feet.bottom <= self.door.bottom

    def unsolved(self, shelf):
        return [d for d in self.content.shelf_documents(shelf) if d["id"] not in self.state.solved]

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        goal = self.robot_aside if "door_open" in self.state.seen else self.robot_guard
        self.robot_pos.move_towards_ip(goal, 180 * dt)
        if self.dialogue.update(dt, events) or self.leaving:
            self.player.update(dt, self.walkable, control=False)
            return
        self.player.update(dt, self.walkable)
        feet = self.player.feet()
        self.near = next((s for s, rect in self.shelves if rect.inflate(REACH * 2, REACH * 2).colliderect(feet)), None)
        self.near_robot = self.robot_rect().inflate(120, 120).colliderect(feet)

        if feet.top > self.floor.bottom + 24:
            self.leaving = True
            from .ending import Ending
            self.scenes.go(lambda: Ending(self.game))
        elif ui.confirm(events):
            if self.near:
                self.open_shelf(self.near)
            elif self.near_robot:
                self.talk_to_robot()

    def open_shelf(self, shelf):
        from .reader import Reader
        self.state.archive_pos = tuple(self.player.pos)
        self.near = None
        assets.play("place.ogg", 0.5)
        self.draw(self.game.screen)        # a clean picture for the reader to sit on
        self.scenes.push(Reader(self.game, shelf))

    def talk_to_robot(self):
        robot = self.content.game["robot"]
        lines = robot["after"] if "door_open" in self.state.seen else robot["blocked"]
        self.dialogue.say([l.format(done=len(self.state.solved), total=self.state.total) for l in lines], robot["name"])

    # ---------------------------------------------------------------- drawing

    def draw(self, screen):
        door_open = "door_open" in self.state.seen
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            if self.stand_in is None or self.stand_in[0] != door_open:
                self.stand_in = (door_open, _stand_in_room(self, door_open))
            screen.blit(self.stand_in[1], (0, 0))
        pulse = 0.5 + 0.5 * math.sin(self.t * 3)
        for shelf, rect in self.shelves:
            if self.unsolved(shelf):
                glow = [int(c * (0.45 + 0.55 * pulse)) for c in settings.TEAL]
                pygame.draw.rect(screen, glow, rect.inflate(24, 24), 8, border_radius=10)
            if shelf is self.near and not self.dialogue.active:
                pygame.draw.rect(screen, settings.CREAM, rect.inflate(8, 8), 4)
        # whoever stands lower on the screen is drawn in front
        robot = (self.robot_pos.y, lambda: screen.blit(self.robot_img, self.robot_img.get_rect(
            midbottom=(round(self.robot_pos.x), round(self.robot_pos.y)))))
        ghost = (self.player.pos.y, lambda: self.player.draw(screen))
        for _, draw in sorted((robot, ghost), key=lambda pair: pair[0]):
            draw()

        ui.draw_text(screen, f"records restored  {len(self.state.solved)} / {self.state.total}", (40, 24), "mono", 26,
                     settings.DIM)
        if self.dialogue.active:
            self.dialogue.draw(screen)
        elif self.near:
            label = self.near["label"] + ("  ·  a memory is caught here" if self.unsolved(self.near) else "")
            ui.panel(screen, (settings.W / 2 - 400, 8, 800, 62))
            ui.draw_text(screen, label, (settings.W / 2, 39), "bold", 36, settings.CREAM, center=True)
            ui.hint(screen, "E — read this shelf")
        elif self.near_robot:
            ui.hint(screen, "E — talk")


# ---------------------------------------------------------------- stand-in art
# Painted small and enlarged, so it looks like the pixel art that will replace it.

def _small(rect):
    k = settings.PIXEL
    return pygame.Rect(rect[0] // k, rect[1] // k, rect[2] // k, rect[3] // k)


def _stand_in_robot():
    img = pygame.Surface((16, 26), pygame.SRCALPHA)
    pygame.draw.rect(img, (96, 104, 116), (2, 8, 12, 14), border_radius=2)
    pygame.draw.rect(img, (124, 132, 146), (3, 0, 10, 9), border_radius=2)
    pygame.draw.rect(img, (255, 96, 80), (5, 3, 2, 2))
    pygame.draw.rect(img, (255, 96, 80), (9, 3, 2, 2))
    pygame.draw.rect(img, (60, 64, 74), (4, 22, 3, 4))
    pygame.draw.rect(img, (60, 64, 74), (9, 22, 3, 4))
    pygame.draw.rect(img, (60, 64, 74), (0, 10, 2, 8))
    pygame.draw.rect(img, (60, 64, 74), (14, 10, 2, 8))
    return img


def _stand_in_room(room, door_open):
    k = settings.PIXEL
    img = pygame.Surface((settings.W // k, settings.H // k))
    floor, door = _small(room.floor), _small(room.door)
    img.fill((34, 30, 34))
    pygame.draw.rect(img, (98, 88, 82), floor)
    for y in range(floor.top + 18, floor.bottom, 18):
        pygame.draw.line(img, (90, 80, 75), (floor.left, y), (floor.right - 1, y))
    pygame.draw.rect(img, (52, 46, 50), (floor.left, 8, floor.width, floor.top - 8))      # back wall
    if room.rug:
        rug = _small(room.rug)
        pygame.draw.rect(img, (124, 74, 66), rug)
        pygame.draw.rect(img, (160, 120, 90), rug.inflate(-8, -8), 1)
    for rect in map(_small, room.obstacles):
        pygame.draw.rect(img, (70, 58, 56), rect)
        pygame.draw.rect(img, (44, 36, 36), rect, 1)
    for _, big in room.shelves:
        rect = _small(big)
        pygame.draw.rect(img, (74, 52, 40), rect)
        pygame.draw.rect(img, (44, 30, 24), rect, 1)
        if rect.width > rect.height:
            for y in range(rect.top + 3, rect.bottom - 6, 11):
                pygame.draw.line(img, (44, 30, 24), (rect.left + 1, y + 9), (rect.right - 2, y + 9))
                for i, x in enumerate(range(rect.left + 3, rect.right - 4, 4)):
                    drop = (i * 5 + y) % 3
                    pygame.draw.rect(img, _BOOKS[(i * 7 + y) % len(_BOOKS)], (x, y + 1 + drop, 3, 8 - drop))
        else:
            for i, y in enumerate(range(rect.top + 3, rect.bottom - 4, 4)):
                pygame.draw.rect(img, _BOOKS[(i * 7) % len(_BOOKS)], (rect.left + 3, y, rect.width - 6, 3))
    pygame.draw.rect(img, (20, 18, 22) if door_open else (86, 62, 44), door.inflate(-4, 0))
    pygame.draw.rect(img, (44, 30, 24), door.inflate(-4, 0), 1)
    return pygame.transform.scale(img, (settings.W, settings.H)).convert()


_BOOKS = [(150, 72, 60), (92, 122, 150), (176, 150, 96), (88, 120, 96), (130, 96, 132), (196, 188, 168)]
