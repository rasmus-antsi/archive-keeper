"""The archive room: the ghost walks between the shelves while the robot guards the door.

Painted art replaces the stand-ins as soon as the files exist:
  assets/img/taustad/arhiiv.png     the whole room, 320x240 (shelves and door included)
  assets/img/tegelased/robot.png    the robot
Keep shelves and the door where data/game.json and the constants below put them.
"""
import math

import pygame

from .. import assets, settings, ui
from ..player import Player
from ..scene import Scene

FLOOR = pygame.Rect(24, 60, 272, 148)
DOOR = pygame.Rect(144, 208, 32, 32)
START = (160, 130)
ROBOT_GUARD = (160, 206)       # feet, in front of the door
ROBOT_ASIDE = (122, 206)
REACH = 10                     # how close to a shelf counts as standing at it


class Archive(Scene):
    music = "archive"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.player = Player(self.state.archive_pos or START)
        self.shelves = [(s, pygame.Rect(s["rect"])) for s in self.content.shelves]
        self.background = assets.optional("taustad/arhiiv.png")
        self.robot_img = assets.optional("tegelased/robot.png") or _stand_in_robot()
        self.robot_pos = pygame.Vector2(ROBOT_ASIDE if "door_open" in self.state.seen else ROBOT_GUARD)
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
        return pygame.Rect(round(self.robot_pos.x) - 8, round(self.robot_pos.y) - 7, 16, 7)

    def walkable(self, feet):
        if feet.colliderect(self.robot_rect()):
            return False
        if FLOOR.contains(feet):
            return True
        # through the doorway, once the robot has stepped aside
        return "door_open" in self.state.seen and DOOR.left <= feet.left and feet.right <= DOOR.right \
            and FLOOR.top <= feet.top and feet.bottom <= DOOR.bottom

    def unsolved(self, shelf):
        return [d for d in self.content.shelf_documents(shelf) if d["id"] not in self.state.solved]

    # ---------------------------------------------------------------- loop

    def update(self, dt, events):
        self.t += dt
        goal = ROBOT_ASIDE if "door_open" in self.state.seen else ROBOT_GUARD
        self.robot_pos.move_towards_ip(goal, 30 * dt)
        if self.dialogue.update(dt, events) or self.leaving:
            self.player.update(dt, self.walkable, control=False)
            return
        self.player.update(dt, self.walkable)
        feet = self.player.feet()
        self.near = next((s for s, rect in self.shelves if rect.inflate(REACH * 2, REACH * 2).colliderect(feet)), None)
        self.near_robot = self.robot_rect().inflate(20, 20).colliderect(feet)

        if feet.top > FLOOR.bottom + 4:
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
        assets.play("place.ogg", 0.5)
        self.scenes.push(Reader(self.game, shelf))

    def talk_to_robot(self):
        robot = self.content.game["robot"]
        lines = robot["after"] if "door_open" in self.state.seen else robot["blocked"]
        self.dialogue.say([l.format(done=len(self.state.solved), total=self.state.total) for l in lines], robot["name"])

    # ---------------------------------------------------------------- drawing

    def draw(self, canvas):
        if self.background:
            canvas.blit(self.background, (0, 0))
        else:
            _stand_in_room(canvas, self.shelves, "door_open" in self.state.seen)
        pulse = 0.5 + 0.5 * math.sin(self.t * 3)
        for shelf, rect in self.shelves:
            if self.unsolved(shelf):
                glow = pygame.Surface(rect.inflate(6, 6).size, pygame.SRCALPHA)
                pygame.draw.rect(glow, (*settings.TEAL, int(60 + 90 * pulse)), glow.get_rect(), 2, border_radius=3)
                canvas.blit(glow, rect.inflate(6, 6))
            if shelf is self.near and not self.dialogue.active:
                pygame.draw.rect(canvas, settings.CREAM, rect.inflate(2, 2), 1)
        # whoever stands lower on the screen is drawn in front
        robot = (self.robot_pos.y, lambda: canvas.blit(self.robot_img, self.robot_img.get_rect(
            midbottom=(round(self.robot_pos.x), round(self.robot_pos.y)))))
        ghost = (self.player.pos.y, lambda: self.player.draw(canvas))
        for _, draw in sorted((robot, ghost), key=lambda pair: pair[0]):
            draw()

    def draw_ui(self, screen):
        if self.scenes.top is not self:
            return
        ui.draw_text(screen, f"records restored  {len(self.state.solved)} / {self.state.total}", (24, 16), "mono", 16,
                     settings.DIM)
        if self.dialogue.active:
            self.dialogue.draw(screen)
        elif self.near:
            label = self.near["label"] + ("  ·  a memory is caught here" if self.unsolved(self.near) else "")
            ui.panel(screen, (settings.W / 2 - 230, 2, 460, 38))
            ui.draw_text(screen, label, (settings.W / 2, 21), "bold", 21, settings.CREAM, center=True)
            ui.hint(screen, "E — read this shelf")
        elif self.near_robot:
            ui.hint(screen, "E — talk")


# ---------------------------------------------------------------- stand-in art

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


def _stand_in_room(canvas, shelves, door_open):
    canvas.fill((34, 30, 34))
    pygame.draw.rect(canvas, (98, 88, 82), FLOOR)
    for y in range(FLOOR.top + 18, FLOOR.bottom, 18):
        pygame.draw.line(canvas, (90, 80, 75), (FLOOR.left, y), (FLOOR.right - 1, y))
    pygame.draw.rect(canvas, (52, 46, 50), (FLOOR.left, 14, FLOOR.width, FLOOR.top - 14))      # back wall
    for _, rect in shelves:
        pygame.draw.rect(canvas, (74, 52, 40), rect)
        pygame.draw.rect(canvas, (44, 30, 24), rect, 1)
        if rect.width > rect.height:
            for y in range(rect.top + 4, rect.bottom - 6, 11):
                pygame.draw.line(canvas, (44, 30, 24), (rect.left + 1, y + 9), (rect.right - 2, y + 9))
                for i, x in enumerate(range(rect.left + 3, rect.right - 4, 4)):
                    pygame.draw.rect(canvas, _BOOKS[(i * 7 + y) % len(_BOOKS)], (x, y + 1 + (i * 5 + y) % 3, 3, 8 - (i * 5 + y) % 3))
        else:
            for i, y in enumerate(range(rect.top + 3, rect.bottom - 4, 4)):
                pygame.draw.rect(canvas, _BOOKS[(i * 7) % len(_BOOKS)], (rect.left + 3, y, rect.width - 6, 3))
    pygame.draw.rect(canvas, (20, 18, 22) if door_open else (86, 62, 44), DOOR.inflate(-4, 0))
    pygame.draw.rect(canvas, (44, 30, 24), DOOR.inflate(-4, 0), 1)


_BOOKS = [(150, 72, 60), (92, 122, 150), (176, 150, 96), (88, 120, 96), (130, 96, 132), (196, 188, 168)]
