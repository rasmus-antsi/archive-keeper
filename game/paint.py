"""Stand-in pixel art, painted in code at the same pixel size as the artists' sprites.

Nothing here is meant to stay: every floor, wall, piece of furniture, roof and item
icon is replaced as soon as a drawn file exists (see game/world.py for the names).
Everything is deterministic, so a room looks the same every time it is painted.
"""
import random

import pygame

BOOKS = [(150, 72, 60), (92, 122, 150), (176, 150, 96), (88, 120, 96), (130, 96, 132), (196, 188, 168)]
TIMBER = (92, 66, 48)


def shade(color, d):
    return tuple(max(0, min(255, c + d)) for c in color[:3])


def rng(*key):
    return random.Random("/".join(str(k) for k in key))


def box(s, rect, color, edge=-38, top=16):
    """A filled block with a dark outline and a lit upper edge."""
    rect = pygame.Rect(rect)
    s.fill(color, rect)
    pygame.draw.rect(s, shade(color, edge), rect, 1)
    if rect.w > 2 and rect.h > 2:
        s.fill(shade(color, top), (rect.x + 1, rect.y + 1, rect.w - 2, 1))


# ---------------------------------------------------------------- floors and walls

FLOORS = {
    "planks": (86, 74, 72), "boards": (150, 116, 84), "threshold": (84, 62, 48),
    "cobble": (148, 140, 128), "grass": (104, 132, 84), "dirt": (140, 114, 84), "tiles": (92, 88, 96),
}
WALLS = {"stone": (62, 60, 76), "plaster": (206, 190, 160), "paper": (132, 104, 98), "log": (124, 92, 62)}


def floor(s, rect, kind, r):
    rect = pygame.Rect(rect)
    base = FLOORS[kind]
    s.fill(base, rect)
    if kind in ("planks", "boards", "threshold"):
        for y in range(rect.top, rect.bottom, 6):
            row = shade(base, r.randint(-5, 5))
            s.fill(row, (rect.left, y, rect.w, 6))
            s.fill(shade(base, -16), (rect.left, y + 5, rect.w, 1))
            x = rect.left + r.randint(6, 40)
            while x < rect.right:
                s.fill(shade(base, -16), (x, y, 1, 5))
                x += r.randint(26, 58)
    elif kind == "cobble":
        s.fill(shade(base, -30), rect)
        for y in range(rect.top, rect.bottom, 5):
            x = rect.left - r.randint(0, 4)
            while x < rect.right:
                w = r.randint(4, 8)
                stone = shade(base, r.randint(-9, 9))
                s.fill(stone, (x, y, w - 1, 4))
                s.fill(shade(stone, 12), (x, y, w - 1, 1))
                x += w
    elif kind == "tiles":
        for y in range(rect.top, rect.bottom, 10):
            for x in range(rect.left, rect.right, 10):
                s.fill(shade(base, 6 if (x // 10 + y // 10) % 2 else -4), (x, y, 9, 9))
    elif kind in ("grass", "dirt"):
        for _ in range(rect.w * rect.h // 28):
            x, y = r.randrange(rect.left, rect.right), r.randrange(rect.top, rect.bottom)
            s.fill(shade(base, r.choice((-14, -8, 10, 16))), (x, y, 1, 2 if kind == "grass" else 1))


def wall(s, rect, kind, r):
    """The back wall of a room, seen from the front."""
    rect = pygame.Rect(rect)
    base = WALLS[kind]
    s.fill(base, rect)
    if kind == "stone":
        for i, y in enumerate(range(rect.top, rect.bottom, 5)):
            s.fill(shade(base, -11), (rect.left, y + 4, rect.w, 1))
            for x in range(rect.left + (6 if i % 2 else 0), rect.right, 12):
                s.fill(shade(base, -11), (x, y, 1, 4))
    elif kind == "plaster":
        for x in range(rect.left + 12, rect.right, 36):
            s.fill(TIMBER, (x, rect.top, 2, rect.h))
    elif kind == "paper":
        for x in range(rect.left + 3, rect.right, 6):
            s.fill(shade(base, 12), (x, rect.top, 1, rect.h))
    elif kind == "log":
        for y in range(rect.top, rect.bottom, 5):
            s.fill(shade(base, -20), (rect.left, y + 4, rect.w, 1))
    s.fill(shade(base, -44), (rect.left, rect.bottom - 2, rect.w, 2))        # skirting board


def wall_top(kind):
    """The colour of a wall seen from above: the thin edges round a room."""
    return shade(WALLS[kind], -50) if kind != "plaster" else (70, 54, 46)


# ---------------------------------------------------------------- furniture and other props

class Spec:
    def __init__(self, paint, size, depth, inset, flat, wall, light):
        self.paint, self.size, self.depth, self.inset = paint, size, depth, inset
        self.flat, self.wall, self.light = flat, wall, light


PROPS = {}       # type -> Spec


def prop(name, size, depth=0, inset=0, flat=False, wall=False, light=None):
    """size is the default picture size. depth is how much of its lower part blocks the
    way (0: nothing), inset narrows that from both sides. flat things lie on the floor,
    wall things hang on the wall behind everybody. light is (radius, colour)."""
    def register(fn):
        PROPS[name] = Spec(fn, size, depth, inset, flat, wall, light)
        return fn
    return register


def make(data):
    """The stand-in picture for one prop from a map."""
    spec = PROPS[data["type"]]
    w, h = data.get("size", spec.size)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    spec.paint(s, w, h, rng(data["type"], w, h, *data.get("pos", (0, 0))), data)
    return s


@prop("bookcase", (60, 30), depth=36)
def _bookcase(s, w, h, r, data):
    box(s, (0, 0, w, h), (98, 68, 50))
    for y in range(2, h - 8, 9):
        s.fill((46, 33, 30), (2, y, w - 4, 8))
        x = 3
        while x < w - 5:
            wide = r.choice((2, 2, 3))
            if r.random() < 0.1:
                x += wide + 1
                continue
            tall = r.randint(5, 7)
            color = r.choice(BOOKS)
            s.fill(color, (x, y + 8 - tall, wide, tall))
            s.fill(shade(color, 34), (x, y + 8 - tall, 1, tall))
            x += wide + (r.random() < 0.25)


@prop("rug", (120, 70), flat=True)
def _rug(s, w, h, r, data):
    base = tuple(data.get("color", (126, 62, 58)))
    s.fill(base)
    pygame.draw.rect(s, shade(base, -30), (0, 0, w, h), 1)
    pygame.draw.rect(s, (188, 150, 100), (3, 3, w - 6, h - 6), 1)
    pygame.draw.rect(s, shade(base, 18), (6, 6, w - 12, h - 12), 1)
    cx, cy = w // 2, h // 2
    pygame.draw.polygon(s, (188, 150, 100), [(cx, cy - h // 5), (cx + w // 6, cy), (cx, cy + h // 5), (cx - w // 6, cy)], 1)
    for x in range(1, w, 3):
        s.fill(shade(base, 40), (x, 0, 1, 1))
        s.fill(shade(base, 40), (x, h - 1, 1, 1))


@prop("sofa", (44, 24), depth=16)
def _sofa(s, w, h, r, data):
    cloth = (98, 56, 66)
    box(s, (2, 0, w - 4, 13), cloth)
    box(s, (2, 10, w - 4, h - 12), shade(cloth, 22))
    s.fill(shade(cloth, -10), (w // 2, 11, 1, h - 14))
    box(s, (0, 6, 6, h - 7), shade(cloth, -8))
    box(s, (w - 6, 6, 6, h - 7), shade(cloth, -8))
    s.fill((60, 42, 36), (2, h - 2, 3, 2))
    s.fill((60, 42, 36), (w - 5, h - 2, 3, 2))


@prop("armchair", (20, 22), depth=16)
def _armchair(s, w, h, r, data):
    cloth = (74, 98, 96)
    box(s, (2, 0, w - 4, 12), cloth)
    box(s, (2, 9, w - 4, h - 11), shade(cloth, 22))
    box(s, (0, 6, 5, h - 7), shade(cloth, -8))
    box(s, (w - 5, 6, 5, h - 7), shade(cloth, -8))


@prop("table", (34, 20), depth=10)
def _table(s, w, h, r, data):
    wood = (146, 108, 72)
    s.fill(shade(wood, -50), (2, h - 6, 2, 6))
    s.fill(shade(wood, -50), (w - 4, h - 6, 2, 6))
    box(s, (0, 0, w, h - 7), wood)
    s.fill(shade(wood, -26), (0, h - 8, w, 3))
    pygame.draw.rect(s, shade(wood, -50), (0, h - 8, w, 3), 1)


@prop("desk", (36, 22), depth=10)
def _desk(s, w, h, r, data):
    _table(s, w, h, r, data)
    box(s, (5, 3, 9, 7), (226, 216, 190), edge=-60)
    box(s, (16, 5, 8, 6), (214, 204, 180), edge=-60)
    s.fill((40, 40, 60), (w - 8, 3, 3, 4))
    s.fill((230, 230, 240), (w - 7, 1, 1, 3))


@prop("stool", (10, 10), depth=6)
def _stool(s, w, h, r, data):
    box(s, (0, 0, w, 6), (132, 96, 62))
    s.fill((70, 50, 38), (1, 6, 2, 4))
    s.fill((70, 50, 38), (w - 3, 6, 2, 4))


@prop("lamp", (12, 30), depth=3, inset=4, light=(64, (236, 190, 120)))
def _lamp(s, w, h, r, data):
    s.fill((52, 44, 44), (5, 9, 2, h - 11))
    box(s, (2, h - 3, 8, 3), (72, 60, 58))
    pygame.draw.polygon(s, (250, 216, 140), [(3, 0), (8, 0), (11, 9), (0, 9)])
    pygame.draw.polygon(s, (170, 124, 70), [(3, 0), (8, 0), (11, 9), (0, 9)], 1)


@prop("sconce", (6, 9), wall=True, light=(46, (230, 176, 110)))
def _sconce(s, w, h, r, data):
    s.fill((70, 62, 60), (2, 4, 2, 5))
    s.fill((250, 214, 130), (1, 0, 4, 4))
    s.fill((255, 244, 200), (2, 1, 2, 2))


@prop("crate", (16, 15), depth=9)
def _crate(s, w, h, r, data):
    wood = (150, 114, 74)
    box(s, (0, 0, w, h), wood)
    pygame.draw.rect(s, shade(wood, -30), (2, 2, w - 4, h - 4), 1)
    pygame.draw.line(s, shade(wood, -30), (2, 2), (w - 3, h - 3))
    s.fill(shade(wood, -38), (0, 5, w, 1))


@prop("barrel", (13, 17), depth=8)
def _barrel(s, w, h, r, data):
    wood = (132, 92, 58)
    pygame.draw.ellipse(s, shade(wood, -40), (0, h - 7, w, 7))
    s.fill(wood, (0, 3, w, h - 6))
    s.fill(shade(wood, -40), (0, 3, 1, h - 6))
    s.fill(shade(wood, -40), (w - 1, 3, 1, h - 6))
    for x in range(3, w - 1, 3):
        s.fill(shade(wood, -16), (x, 4, 1, h - 7))
    pygame.draw.ellipse(s, shade(wood, 26), (0, 0, w, 7))
    pygame.draw.ellipse(s, shade(wood, -40), (0, 0, w, 7), 1)
    s.fill((78, 78, 86), (0, 7, w, 1))
    s.fill((78, 78, 86), (0, h - 5, w, 1))


@prop("chest", (22, 16), depth=9)
def _chest(s, w, h, r, data):
    wood = (124, 82, 50)
    box(s, (0, 6, w, h - 6), wood)
    box(s, (0, 0, w, 8), shade(wood, 22))
    for x in (3, w - 5):
        s.fill((196, 164, 84), (x, 0, 2, h))
    box(s, (w // 2 - 2, 6, 4, 5), (226, 194, 96), edge=-70)


@prop("cabinet", (24, 34), depth=8)
def _cabinet(s, w, h, r, data):
    wood = (108, 74, 52)
    box(s, (0, 0, w, h), wood)
    s.fill(shade(wood, 26), (0, 0, w, 2))
    box(s, (2, 4, w // 2 - 2, h - 8), shade(wood, 12))
    box(s, (w // 2, 4, w // 2 - 2, h - 8), shade(wood, 12))
    s.fill((224, 190, 110), (w // 2 - 3, h // 2, 2, 2))
    s.fill((224, 190, 110), (w // 2 + 1, h // 2, 2, 2))
    s.fill(shade(wood, -50), (1, h - 2, 3, 2))
    s.fill(shade(wood, -50), (w - 4, h - 2, 3, 2))


@prop("dresser", (26, 20), depth=8)
def _dresser(s, w, h, r, data):
    wood = (136, 96, 62)
    box(s, (0, 0, w, h), wood)
    s.fill(shade(wood, 24), (0, 0, w, 3))
    for y in (4, 9, 14):
        box(s, (2, y, w - 4, 5), shade(wood, 10))
        s.fill((224, 190, 110), (w // 2 - 1, y + 2, 2, 1))


@prop("bed", (24, 38), depth=34)
def _bed(s, w, h, r, data):
    box(s, (0, 0, w, h), (98, 68, 48))
    s.fill((232, 224, 204), (2, 5, w - 4, h - 8))
    box(s, (4, 6, w - 8, 7), (250, 246, 236), edge=-40)
    cloth = tuple(data.get("color", (86, 106, 142)))
    box(s, (2, 16, w - 4, h - 19), cloth)
    s.fill(shade(cloth, 34), (2, 20, w - 4, 2))
    s.fill((70, 48, 36), (0, 0, w, 4))


@prop("stove", (26, 32), depth=10, light=(40, (236, 150, 80)))
def _stove(s, w, h, r, data):
    tile = (210, 202, 188)
    box(s, (0, 0, w, h), tile)
    for y in range(6, h - 2, 6):
        s.fill(shade(tile, -24), (1, y, w - 2, 1))
    for x in range(6, w - 2, 7):
        s.fill(shade(tile, -24), (x, 1, 1, h - 2))
    box(s, (w // 2 - 5, h - 12, 10, 9), (44, 40, 44))
    s.fill((244, 150, 60), (w // 2 - 3, h - 8, 6, 3))
    s.fill((255, 220, 120), (w // 2 - 1, h - 7, 2, 2))
    s.fill(shade(tile, -40), (0, 0, w, 2))


@prop("well", (26, 26), depth=22)
def _well(s, w, h, r, data):
    stone = (140, 136, 130)
    pygame.draw.ellipse(s, shade(stone, -40), (0, 8, w, h - 8))
    pygame.draw.ellipse(s, stone, (1, 7, w - 2, h - 10))
    pygame.draw.ellipse(s, (44, 66, 92), (5, 10, w - 10, h - 17))
    pygame.draw.ellipse(s, (84, 116, 150), (8, 12, 6, 2))
    s.fill(TIMBER, (2, 0, 2, 16))
    s.fill(TIMBER, (w - 4, 0, 2, 16))
    box(s, (1, 0, w - 2, 3), (124, 90, 62))
    s.fill((60, 50, 44), (w // 2, 3, 1, 7))
    box(s, (w // 2 - 2, 9, 5, 4), (150, 110, 70))


@prop("tree", (34, 46), depth=5, inset=13)
def _tree(s, w, h, r, data):
    s.fill((84, 60, 44), (w // 2 - 2, h - 16, 5, 16))
    s.fill((60, 42, 32), (w // 2 - 2, h - 16, 1, 16))
    leaf = (72, 112, 68)
    for cx, cy, rad, d in ((w // 2, 20, 16, -18), (11, 22, 10, -8), (w - 11, 22, 10, -8), (w // 2, 14, 13, 0),
                           (w // 2 - 4, 10, 8, 14)):
        pygame.draw.circle(s, shade(leaf, d), (cx, cy), rad)
    for _ in range(26):
        x, y = r.randrange(5, w - 5), r.randrange(4, 30)
        if s.get_at((x, y))[3]:
            s.fill(shade(leaf, r.choice((-24, 22))), (x, y, 2, 1))


@prop("bush", (16, 11), depth=5)
def _bush(s, w, h, r, data):
    leaf = (80, 120, 72)
    pygame.draw.ellipse(s, shade(leaf, -22), (0, 2, w, h - 2))
    pygame.draw.ellipse(s, leaf, (1, 0, w - 5, h - 3))
    for _ in range(5):
        s.fill((214, 120, 110), (r.randrange(3, w - 3), r.randrange(2, h - 4), 1, 1))


@prop("post", (8, 34), depth=3, inset=2, light=(50, (240, 200, 130)))
def _post(s, w, h, r, data):
    s.fill((48, 46, 52), (3, 8, 2, h - 8))
    s.fill((48, 46, 52), (2, h - 2, 4, 2))
    box(s, (1, 0, 6, 8), (250, 220, 140), edge=-150)


@prop("bench", (28, 13), depth=6)
def _bench(s, w, h, r, data):
    wood = (140, 102, 66)
    box(s, (0, 0, w, 5), wood)
    box(s, (0, 6, w, 4), shade(wood, 14))
    s.fill((64, 46, 36), (2, 10, 2, 3))
    s.fill((64, 46, 36), (w - 4, 10, 2, 3))


@prop("fence", (60, 11), depth=3)
def _fence(s, w, h, r, data):
    wood = (150, 124, 92)
    s.fill(shade(wood, -20), (0, 4, w, 1))
    s.fill(shade(wood, -20), (0, 8, w, 1))
    for x in range(0, w, 5):
        s.fill(wood, (x, 1, 3, h - 1))
        s.fill(shade(wood, 24), (x + 1, 0, 1, 1))
        s.fill(shade(wood, -34), (x + 2, 1, 1, h - 1))


@prop("machine", (28, 36), depth=9, light=(40, (110, 220, 210)))
def _machine(s, w, h, r, data):
    metal = (66, 70, 84)
    box(s, (0, 0, w, h), metal)
    box(s, (3, 4, w - 6, 12), (20, 44, 48), edge=-10, top=0)
    for y in (6, 9, 12):
        s.fill((130, 226, 214), (5, y, r.randint(6, w - 12), 1))
    for i, color in enumerate(((230, 80, 70), (240, 200, 90), (110, 220, 140))):
        s.fill(color, (4 + i * 4, 19, 2, 2))
    for y in range(24, h - 3, 3):
        s.fill(shade(metal, -26), (4, y, w - 8, 1))
    s.fill(shade(metal, -40), (0, h - 2, w, 2))


@prop("boxes", (18, 20), depth=8)
def _boxes(s, w, h, r, data):
    paper = (182, 160, 124)
    box(s, (0, 9, w, h - 9), paper)
    box(s, (2, 0, w - 5, 10), shade(paper, 14))
    box(s, (4, 13, 7, 4), (232, 224, 204), edge=-70)
    box(s, (5, 3, 6, 3), (232, 224, 204), edge=-70)


@prop("plant", (14, 22), depth=4, inset=3)
def _plant(s, w, h, r, data):
    box(s, (3, h - 8, 8, 8), (160, 96, 70))
    leaf = (76, 124, 84)
    for x, y, rad in ((7, 8, 6), (3, 11, 4), (10, 11, 4), (7, 4, 4)):
        pygame.draw.circle(s, shade(leaf, r.randint(-14, 14)), (x, y), rad)


@prop("door", (20, 28), wall=True)
def _door(s, w, h, r, data):
    box(s, (0, 0, w, h), (64, 48, 42))
    if data.get("open"):
        s.fill((12, 11, 16), (2, 2, w - 4, h - 2))
        s.fill((40, 44, 60), (2, h - 6, w - 4, 6))
    else:
        wood = (128, 90, 58)
        box(s, (2, 2, w - 4, h - 2), wood)
        box(s, (4, 4, w - 8, 9), shade(wood, -14))
        box(s, (4, 15, w - 8, 10), shade(wood, -14))
        s.fill((226, 194, 110), (w - 6, 14, 2, 2))


@prop("window", (16, 13), wall=True)
def _window(s, w, h, r, data):
    box(s, (0, 0, w, h), (92, 66, 48))
    s.fill((170, 206, 220), (2, 2, w - 4, h - 4))
    s.fill((214, 236, 240), (3, 3, 3, 2))
    s.fill((92, 66, 48), (w // 2, 2, 1, h - 4))
    s.fill((92, 66, 48), (2, h // 2, w - 4, 1))


@prop("picture", (12, 10), wall=True)
def _picture(s, w, h, r, data):
    box(s, (0, 0, w, h), (170, 136, 70))
    s.fill((96, 124, 140), (2, 2, w - 4, h - 4))
    s.fill((120, 150, 110), (2, h - 5, w - 4, 3))


# Types the artists drew and nobody painted a stand-in for: the picture is
# assets/img/props/<type>.png, and until that file exists the prop is a pink box.

def _undrawn(s, w, h, r, data):
    s.fill((200, 60, 120, 200))
    pygame.draw.rect(s, (255, 255, 255), (0, 0, w, h), 1)


def drawn(name, size, depth=0, inset=0, flat=False, wall=False, light=None):
    """Register a drawn type. The numbers mean the same as for prop()."""
    PROPS[name] = Spec(_undrawn, size, depth, inset, flat, wall, light)


# the archive
drawn("clock", (23, 59), depth=6, inset=3)
drawn("sidetable", (17, 18), depth=8)
drawn("cupboard", (50, 36), depth=16)
drawn("bookcase-side", (16, 65), depth=40)
drawn("cupboard-side", (16, 53), depth=30)
# the town hall square in winter
drawn("houses", (214, 68), depth=68)
drawn("townhall", (33, 192), depth=192)
drawn("fountain", (80, 78), depth=46, inset=3)
drawn("spruce", (80, 166), depth=18, inset=24)
drawn("streetlamp", (20, 66), depth=4, inset=7)
drawn("snow", (52, 23), depth=10, inset=4)
drawn("gallows", (32, 46), depth=5, inset=1)


def robot():
    img = pygame.Surface((16, 26), pygame.SRCALPHA)
    box(img, (2, 8, 12, 14), (96, 104, 116))
    box(img, (3, 0, 10, 9), (124, 132, 146))
    img.fill((255, 96, 80), (5, 3, 2, 2))
    img.fill((255, 96, 80), (9, 3, 2, 2))
    img.fill((60, 64, 74), (4, 22, 3, 4))
    img.fill((60, 64, 74), (9, 22, 3, 4))
    return img


# ---------------------------------------------------------------- roofs

ROOFS = {"tile": (156, 82, 64), "thatch": (178, 152, 98), "shingle": (112, 98, 92)}
FACADE = 15      # how much of the front wall shows under the eaves


def roof(w, h, kind, door_xs, wall_kind, r):
    """A house seen from outside: the roof, and under it the front wall with its door."""
    s = pygame.Surface((w, h))
    base = ROOFS[kind]
    top = h - FACADE
    s.fill(base)
    for i, y in enumerate(range(0, top, 4)):
        lit = 10 if y < top // 2 else -8          # the far slope catches the light
        s.fill(shade(base, lit + r.randint(-4, 4)), (0, y, w, 4))
        s.fill(shade(base, -26), (0, y + 3, w, 1))
        if kind != "thatch":
            for x in range(3 if i % 2 else 0, w, 6):
                s.fill(shade(base, -26), (x, y, 1, 3))
    s.fill(shade(base, 34), (0, top // 2 - 1, w, 2))             # ridge
    s.fill(shade(base, -50), (0, top - 2, w, 2))                 # eaves
    pygame.draw.rect(s, shade(base, -50), (0, 0, w, top), 1)
    box(s, (w * 2 // 3, top // 2 - 12, 9, 10), (122, 80, 70))    # chimney
    s.fill((40, 34, 36), (w * 2 // 3 + 2, top // 2 - 10, 5, 3))

    front = WALLS.get(wall_kind, WALLS["plaster"])
    s.fill(front, (0, top, w, FACADE))
    s.fill(shade(front, -50), (0, h - 2, w, 2))
    s.fill(TIMBER, (0, top, 2, FACADE))
    s.fill(TIMBER, (w - 2, top, 2, FACADE))
    taken = [(x - 12, x + 26) for x in door_xs]
    for x in range(10, w - 22, 26):
        if all(x + 12 < a or x > b for a, b in taken):
            box(s, (x, top + 3, 11, 8), (88, 64, 48))
            s.fill((60, 78, 96), (x + 2, top + 5, 7, 4))
            s.fill((88, 64, 48), (x + 5, top + 5, 1, 4))
    for x in door_xs:
        box(s, (x - 1, top + 1, 16, FACADE - 1), (70, 50, 40))
        box(s, (x + 1, top + 3, 12, FACADE - 3), (132, 92, 58))
        s.fill((226, 194, 110), (x + 10, top + 9, 2, 2))
    return s.convert()


# ---------------------------------------------------------------- things found in chests and cupboards

ICONS = {}


def icon(name):
    """A 16x16 stand-in picture of an item, until the artists draw it."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    ICONS.get(name, _parcel)(s)
    return s


def _icon(name):
    def register(fn):
        ICONS[name] = fn
        return fn
    return register


def _parcel(s):
    box(s, (2, 4, 12, 10), (176, 150, 110))
    s.fill((120, 70, 60), (7, 4, 2, 10))
    s.fill((120, 70, 60), (2, 8, 12, 2))


@_icon("candle")
def _candle(s):
    box(s, (3, 12, 10, 3), (190, 160, 84))
    box(s, (6, 5, 4, 8), (236, 228, 204), edge=-50)
    s.fill((60, 50, 44), (8, 3, 1, 2))
    s.fill((250, 180, 70), (7, 1, 2, 3))
    s.fill((255, 240, 170), (8, 2, 1, 1))


@_icon("book")
def _book(s):
    box(s, (2, 3, 12, 11), (128, 64, 58))
    s.fill((230, 222, 200), (4, 12, 9, 1))
    s.fill((210, 176, 96), (5, 5, 6, 1))
    s.fill((210, 176, 96), (5, 7, 4, 1))
    s.fill((84, 40, 38), (3, 4, 1, 9))


@_icon("watch")
def _watch(s):
    pygame.draw.line(s, (190, 160, 84), (8, 4), (13, 0))
    pygame.draw.circle(s, (150, 120, 60), (7, 9), 6)
    pygame.draw.circle(s, (240, 234, 214), (7, 9), 4)
    s.fill((40, 34, 34), (7, 6, 1, 4))
    s.fill((40, 34, 34), (7, 9, 3, 1))
    s.fill((190, 160, 84), (6, 2, 3, 2))


@_icon("typewriter")
def _typewriter(s):
    box(s, (1, 7, 14, 7), (52, 52, 60))
    box(s, (3, 3, 10, 5), (72, 72, 82))
    s.fill((236, 230, 212), (5, 0, 6, 4))
    for y in (9, 11):
        for x in range(3, 13, 2):
            s.fill((214, 208, 196), (x, y, 1, 1))
    s.fill((150, 150, 160), (1, 4, 2, 1))
    s.fill((150, 150, 160), (13, 4, 2, 1))


@_icon("key")
def _key(s):
    pygame.draw.circle(s, (206, 172, 88), (5, 5), 4, 2)
    pygame.draw.line(s, (206, 172, 88), (7, 7), (13, 13), 2)
    s.fill((206, 172, 88), (10, 12, 2, 3))
    s.fill((150, 118, 56), (12, 13, 2, 2))


@_icon("bottle")
def _bottle(s):
    box(s, (5, 6, 6, 9), (70, 120, 96))
    s.fill((70, 120, 96), (7, 2, 2, 4))
    s.fill((150, 110, 70), (7, 1, 2, 2))
    s.fill((150, 200, 170), (6, 8, 1, 5))
    box(s, (5, 9, 6, 3), (228, 218, 190), edge=-60)


@_icon("inkwell")
def _inkwell(s):
    box(s, (3, 8, 10, 7), (44, 46, 70))
    s.fill((20, 20, 34), (5, 7, 6, 2))
    pygame.draw.line(s, (236, 232, 220), (9, 8), (14, 0), 2)
    s.fill((120, 130, 190), (4, 10, 1, 3))


@_icon("spyglass")
def _spyglass(s):
    pygame.draw.line(s, (190, 156, 80), (2, 13), (7, 8), 4)
    pygame.draw.line(s, (120, 84, 54), (7, 8), (13, 2), 5)
    pygame.draw.circle(s, (170, 210, 226), (13, 2), 2)
    s.fill((240, 214, 130), (4, 10, 1, 1))


@_icon("letters")
def _letters(s):
    box(s, (2, 5, 11, 8), (226, 216, 190), edge=-70)
    box(s, (4, 3, 11, 8), (238, 230, 206), edge=-70)
    pygame.draw.line(s, (150, 136, 110), (4, 3), (9, 7))
    pygame.draw.line(s, (150, 136, 110), (14, 3), (9, 7))
    s.fill((170, 60, 54), (8, 7, 3, 3))


@_icon("compass")
def _compass(s):
    pygame.draw.circle(s, (176, 140, 70), (8, 8), 7)
    pygame.draw.circle(s, (236, 228, 204), (8, 8), 5)
    pygame.draw.line(s, (190, 60, 50), (8, 8), (8, 4))
    pygame.draw.line(s, (50, 50, 60), (8, 8), (8, 12))
