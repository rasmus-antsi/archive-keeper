"""Generates placeholder art and sound into assets/.

Run from the project root:  venv/bin/python tools/make_placeholders.py
(needs: pip install soundfile numpy; these are tool-only, not game dependencies)

Everything it writes is meant to be replaced: drop a real file with the same
name into assets/img or assets/snd and the game picks it up. The map is
painted from game/layout.py at world size, one pixel per world pixel.
"""
import json
import math
import os
import random
import struct
import sys
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame

from game import layout

pygame.init()
pygame.display.set_mode((1, 1))

IMG = "assets/img"
SND = "assets/snd"
FONTS = "assets/fonts"
rnd = random.Random(7)


def font(kind, size):
    name = {
        "serif": "CrimsonText-Regular.ttf",
        "italic": "CrimsonText-Italic.ttf",
        "bold": "CrimsonText-SemiBold.ttf",
        "mono": "CourierPrime-Regular.ttf",
    }[kind]
    return pygame.font.Font(f"{FONTS}/{name}", size)


def save(surf, name):
    path = f"{IMG}/{name}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pygame.image.save(surf, path)
    print("wrote", path)


def vgrad(size, top, bottom):
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(h):
        k = y / max(1, h - 1)
        col = [round(top[i] + (bottom[i] - top[i]) * k) for i in range(3)]
        pygame.draw.line(surf, col, (0, y), (w, y))
    return surf


def grain(surf, count, light=(255, 255, 255), dark=(0, 0, 0), alpha=14):
    w, h = surf.get_size()
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(count):
        col = light if rnd.random() < 0.5 else dark
        s = rnd.choice((1, 1, 2, 3))
        layer.fill((*col, rnd.randint(4, alpha)), (rnd.randrange(w), rnd.randrange(h), s, s))
    surf.blit(layer, (0, 0))


def glow(surf, pos, radius, color, strength=1.0):
    g = pygame.Surface((radius * 2, radius * 2))
    steps = 40
    for i in range(steps):
        k = 1 - i / steps
        a = strength * (1 - k) ** 2 * 0.5
        pygame.draw.circle(g, [round(c * a) for c in color], (radius, radius), round(radius * k))
    surf.blit(g, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGB_ADD)


def label(surf, text, pos, kind="mono", size=30, color=(255, 255, 255), center=False, alpha=255):
    img = font(kind, size).render(text, True, color)
    img.set_alpha(alpha)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)
    return rect


def shade(color, k):
    return tuple(max(0, min(255, round(c * k))) for c in color)


def shadow(surf, rect, radius=10, offset=(6, 10), alpha=70):
    sh = pygame.Surface((rect.w + 40, rect.h + 40), pygame.SRCALPHA)
    pygame.draw.rect(sh, (20, 10, 10, alpha), (20, 20, rect.w, rect.h), border_radius=radius)
    sh = pygame.transform.gaussian_blur(sh, 8)
    surf.blit(sh, (rect.x - 20 + offset[0], rect.y - 20 + offset[1]))


# ---------------------------------------------------------------- ghost and small sprites

def make_ghost():
    w, h = 220, 280
    body = pygame.Surface((w, h), pygame.SRCALPHA)
    col = (236, 250, 244, 244)
    pygame.draw.ellipse(body, col, (30, 20, 160, 170))
    pts = [(30, 105)]
    for i in range(0, 161, 8):
        x = 30 + i
        pts.append((x, 215 + math.sin(i / 160 * math.pi * 3.5) * 22 + (i / 160) * 14))
    pts.append((190, 105))
    pygame.draw.polygon(body, col, pts)
    body = pygame.transform.gaussian_blur(body, 3)
    lines = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(24, 250, 9):
        pygame.draw.line(lines, (120, 200, 205, 26), (34, y), (186, y), 3)
    body.blit(lines, (0, 0))
    mask = pygame.mask.from_surface(body, 40).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    for ex in (84, 136):
        pygame.draw.ellipse(body, (36, 62, 78), (ex - 12, 78, 24, 34))
        pygame.draw.circle(body, (240, 255, 255), (ex + 4, 88), 6)
    pygame.draw.ellipse(body, (255, 170, 150, 120), (52, 118, 28, 16))
    pygame.draw.ellipse(body, (255, 170, 150, 120), (140, 118, 28, 16))
    pygame.draw.arc(body, (36, 62, 78), (96, 110, 28, 20), math.pi * 1.1, math.pi * 1.9, 4)
    save(body, "ghost.png")


def make_small():
    for i in range(4):
        st = pygame.Surface((120, 150), pygame.SRCALPHA)
        for y in range(0, 150, 10):
            for x in range(0, 120, 10):
                if rnd.random() < 0.62:
                    v = rnd.randint(90, 230)
                    st.fill((v // 2, v, v, rnd.randint(60, 210)), (x, y, 10, 10))
        pygame.draw.rect(st, (120, 220, 215, 220), (0, 0, 120, 150), 3)
        save(st, f"static_{i}.png")

    coats = ((176, 84, 70), (84, 116, 150), (104, 140, 96), (200, 160, 84), (140, 100, 150))
    hairs = ((70, 48, 36), (210, 190, 140), (40, 36, 40), (150, 90, 50), (230, 226, 220))
    for i in range(5):
        v = pygame.Surface((56, 80), pygame.SRCALPHA)
        pygame.draw.ellipse(v, (20, 10, 10, 60), (8, 62, 40, 16))
        pygame.draw.ellipse(v, coats[i], (10, 30, 36, 42))
        pygame.draw.ellipse(v, shade(coats[i], 0.8), (10, 52, 36, 20))
        pygame.draw.circle(v, (236, 200, 170), (28, 22), 15)
        pygame.draw.circle(v, hairs[i], (28, 17), 15, draw_top_left=True, draw_top_right=True)
        save(v, f"visitor_{i}.png")

    w, h = 1700, 960
    s = vgrad((w, h), (246, 236, 212), (232, 218, 188))
    for y in range(120, h - 40, 46):
        pygame.draw.line(s, (212, 198, 168), (60, y), (w - 60, y), 1)
    pygame.draw.rect(s, (160, 66, 52), (0, 0, w, 14))
    grain(s, 9000, (255, 255, 255), (90, 70, 40), 18)
    shaped = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(shaped, (255, 255, 255), (0, 0, w, h), border_radius=18)
    s.blit(shaped, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    save(s, "card.png")


# ---------------------------------------------------------------- the map

FLOORS = {"fuajee": (206, 158, 104), "linn": (198, 152, 104), "vald": (190, 138, 92), "hoim": (200, 150, 100)}
WALL_TOP = (112, 78, 64)
WALL_FACE = (236, 214, 176)


def planks(surf, rect, base):
    x0, y0, w, h = rect
    pygame.draw.rect(surf, base, rect)
    for y in range(y0, y0 + h, 46):
        x = x0 - rnd.randint(0, 200)
        while x < x0 + w:
            length = rnd.randint(180, 340)
            r = pygame.Rect(x, y, length, 46).clip(pygame.Rect(rect))
            if r.w > 0:
                pygame.draw.rect(surf, shade(base, rnd.uniform(0.93, 1.06)), r)
                pygame.draw.line(surf, shade(base, 0.8), (r.right - 1, r.y), (r.right - 1, r.bottom - 1), 2)
            x += length
        pygame.draw.line(surf, shade(base, 0.8), (x0, y), (x0 + w, y), 2)


def rug(surf, cx, cy, w, h, color, kind="rug"):
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (cx, cy)
    if kind == "rug_round":
        pygame.draw.ellipse(surf, shade(color, 0.7), rect.inflate(16, 16))
        pygame.draw.ellipse(surf, color, rect)
        pygame.draw.ellipse(surf, shade(color, 1.25), rect.inflate(-60, -60), 6)
        pygame.draw.ellipse(surf, shade(color, 0.85), rect.inflate(-150, -150))
        return
    pygame.draw.rect(surf, shade(color, 0.7), rect.inflate(14, 14), border_radius=6)
    pygame.draw.rect(surf, color, rect, border_radius=4)
    pygame.draw.rect(surf, (238, 222, 190), rect.inflate(-26, -26), 4, border_radius=4)
    if kind == "rug_woven":
        cream = (240, 226, 196)
        for x in range(rect.x + 50, rect.right - 50, 60):
            for y in range(rect.y + 50, rect.bottom - 30, 60):
                pygame.draw.polygon(surf, cream, [(x, y - 18), (x + 18, y), (x, y + 18), (x - 18, y)], 4)
                pygame.draw.rect(surf, cream, (x - 4, y - 4, 8, 8))
    for x in range(rect.x + 6, rect.right, 14):
        pygame.draw.line(surf, shade(color, 1.2), (x, rect.y - 12), (x, rect.y - 4), 2)
        pygame.draw.line(surf, shade(color, 1.2), (x, rect.bottom + 4), (x, rect.bottom + 12), 2)


def prop(surf, kind, cx, cy, w, h, accent):
    wood, dark = (140, 96, 62), (96, 64, 44)
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (cx, cy)
    if kind in ("rug", "rug_round", "rug_woven"):
        rug(surf, cx, cy, w, h, accent, kind)
    elif kind in ("table", "desk"):
        shadow(surf, rect)
        pygame.draw.rect(surf, dark, rect.move(0, 10), border_radius=10)
        pygame.draw.rect(surf, wood, rect, border_radius=10)
        pygame.draw.rect(surf, shade(wood, 1.15), rect.inflate(-16, -16), 3, border_radius=8)
        for _ in range(3):
            px, py = rnd.randint(rect.x + 16, rect.right - 70), rnd.randint(rect.y + 12, rect.bottom - 50)
            paper = pygame.Surface((52, 38), pygame.SRCALPHA)
            paper.fill((244, 236, 214) if kind == "desk" or rnd.random() < 0.5 else (150, 180, 214))
            for ly in range(8, 34, 8):
                pygame.draw.line(paper, (120, 110, 100), (6, ly), (46 - rnd.randint(0, 16), ly), 2)
            surf.blit(pygame.transform.rotate(paper, rnd.randint(-18, 18)), (px, py))
    elif kind in ("shelf", "shelf_low", "cabinet"):
        shadow(surf, rect)
        pygame.draw.rect(surf, dark, rect.move(0, 12), border_radius=6)
        pygame.draw.rect(surf, shade(wood, 0.85), rect, border_radius=6)
        books = ((170, 70, 60), (70, 104, 140), (210, 170, 90), (96, 130, 96), (230, 220, 200), (120, 80, 120))
        if rect.h > rect.w:
            for y in range(rect.y + 8, rect.bottom - 10, 12):
                pygame.draw.rect(surf, rnd.choice(books), (rect.x + 8, y, rect.w - 16, 9), border_radius=2)
        else:
            for x in range(rect.x + 8, rect.right - 10, 12):
                pygame.draw.rect(surf, rnd.choice(books), (x, rect.y + 8, 9, rect.h - 16), border_radius=2)
    elif kind == "bench":
        shadow(surf, rect)
        pygame.draw.rect(surf, dark, rect.move(0, 8), border_radius=8)
        pygame.draw.rect(surf, shade(wood, 1.1), rect, border_radius=8)
        for x in range(rect.x + 30, rect.right, 60):
            pygame.draw.line(surf, shade(wood, 0.85), (x, rect.y + 4), (x, rect.bottom - 4), 2)
    elif kind == "chair":
        r = pygame.Rect(cx - 24, cy - 24, 48, 48)
        shadow(surf, r, offset=(4, 6))
        pygame.draw.rect(surf, shade(wood, 1.05), r, border_radius=10)
        pygame.draw.rect(surf, accent, r.inflate(-14, -14), border_radius=8)
    elif kind == "sofa":
        shadow(surf, rect)
        pygame.draw.rect(surf, shade(accent, 0.75), rect.inflate(16, 20), border_radius=22)
        pygame.draw.rect(surf, accent, rect, border_radius=16)
        pygame.draw.line(surf, shade(accent, 0.8), (cx, rect.y + 8), (cx, rect.bottom - 8), 3)
        pygame.draw.rect(surf, (240, 220, 180), (rect.x + 14, rect.y + 12, 44, 40), border_radius=10)
    elif kind == "plant":
        sh = pygame.Rect(cx - 34, cy - 4, 76, 50)
        shadow(surf, sh, radius=24, offset=(4, 8))
        pygame.draw.circle(surf, (168, 96, 66), (cx, cy), 28)
        pygame.draw.circle(surf, (120, 66, 46), (cx, cy), 28, 5)
        for i in range(9):
            a = i / 9 * math.tau + rnd.uniform(-0.2, 0.2)
            d = rnd.randint(18, 34)
            leaf = (cx + math.cos(a) * d, cy - 8 + math.sin(a) * d)
            pygame.draw.circle(surf, rnd.choice(((84, 140, 86), (104, 160, 96), (70, 120, 80))), leaf, rnd.randint(14, 20))
        pygame.draw.circle(surf, (120, 176, 108), (cx, cy - 8), 14)
    elif kind == "lamp":
        glow(surf, (cx, cy), 300, (255, 196, 110), 0.8)
        pygame.draw.circle(surf, (96, 64, 44), (cx, cy + 6), 16)
        pygame.draw.circle(surf, (255, 226, 160), (cx, cy), 22)
        pygame.draw.circle(surf, (255, 246, 214), (cx, cy), 12)
    elif kind == "stove":
        shadow(surf, rect)
        pygame.draw.rect(surf, (226, 218, 204), rect, border_radius=8)
        pygame.draw.rect(surf, (180, 170, 158), rect, 5, border_radius=8)
        for x in range(rect.x + 10, rect.right - 10, 26):
            for y in range(rect.y + 10, rect.bottom - 10, 26):
                pygame.draw.rect(surf, (206, 196, 182), (x, y, 22, 22), 2)
        glow(surf, (cx, rect.bottom + 10), 150, (255, 140, 60), 0.9)
    elif kind == "crate":
        shadow(surf, rect)
        pygame.draw.rect(surf, (176, 132, 84), rect, border_radius=4)
        pygame.draw.rect(surf, dark, rect, 4, border_radius=4)
        pygame.draw.line(surf, dark, rect.topleft, rect.bottomright, 4)
    elif kind == "cart":
        shadow(surf, rect)
        pygame.draw.rect(surf, (110, 120, 130), rect, border_radius=8)
        for i in range(3):
            pygame.draw.rect(surf, (240, 232, 210), (rect.x + 12 + i * 32, rect.y + 10, 24, rect.h - 20), border_radius=3)
        for dx in (10, rect.w - 10):
            pygame.draw.circle(surf, (50, 50, 56), (rect.x + dx, rect.bottom + 4), 8)
    elif kind == "loom":
        shadow(surf, rect)
        pygame.draw.rect(surf, wood, rect, 10, border_radius=6)
        for x in range(rect.x + 14, rect.right - 12, 8):
            pygame.draw.line(surf, (240, 226, 196), (x, rect.y + 10), (x, rect.bottom - 10), 2)
        pygame.draw.rect(surf, accent, (rect.x + 12, rect.y + 12, rect.w - 24, 36))


def make_map():
    W, H = layout.WORLD
    s = pygame.Surface((W, H))
    s.fill((36, 26, 28))
    rooms = {k: pygame.Rect(v) for k, v in layout.ROOMS.items()}
    doors = {k: pygame.Rect(w["door"]) for k, w in layout.WINGS.items()}
    # walls first, then floors cut into them
    for r in rooms.values():
        outer = pygame.Rect(r.x - 40, r.y - 110, r.w + 80, r.h + 150)
        sh = pygame.Surface((outer.w + 120, outer.h + 120), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 120), (60, 60, outer.w, outer.h), border_radius=18)
        s.blit(pygame.transform.gaussian_blur(sh, 24), (outer.x - 60 + 10, outer.y - 60 + 24))
    for r in rooms.values():
        pygame.draw.rect(s, WALL_TOP, (r.x - 40, r.y - 110, r.w + 80, r.h + 150), border_radius=14)
    for name, r in rooms.items():
        planks(s, r, FLOORS[name])
        face = pygame.Rect(r.x, r.y - 70, r.w, 70)
        pygame.draw.rect(s, WALL_FACE, face)
        pygame.draw.rect(s, shade(WALL_FACE, 0.86), (face.x, face.bottom - 20, face.w, 20))
        pygame.draw.line(s, shade(WALL_FACE, 0.7), (face.x, face.bottom - 20), (face.right, face.bottom - 20), 2)
        # soft shadow the wall drops on the floor
        for i in range(26):
            line = pygame.Surface((r.w, 1), pygame.SRCALPHA)
            line.fill((40, 20, 10, int(70 * (1 - i / 26))))
            s.blit(line, (r.x, r.y + i))
        # windows with a night sky and warm curtains
        for wx in range(r.x + 60, r.right - 100, 300):
            pygame.draw.rect(s, (60, 70, 110), (wx, face.y + 8, 80, 38), border_radius=4)
            pygame.draw.rect(s, (150, 60, 50), (wx - 6, face.y + 4, 22, 46), border_radius=4)
            pygame.draw.rect(s, (150, 60, 50), (wx + 64, face.y + 4, 22, 46), border_radius=4)
    for d in doors.values():
        planks(s, d, shade(FLOORS["fuajee"], 0.94))
        pygame.draw.rect(s, shade(FLOORS["fuajee"], 0.7), d, 4)
    # props
    for name, items in layout.PROPS.items():
        accent = layout.WINGS[name]["accent"] if name in layout.WINGS else (178, 82, 62)
        for kind, x, y, w, h in items:
            prop(s, kind, x, y, w, h, accent)
    # plinths
    for spots in layout.PLINTHS.values():
        for x, y in spots:
            r = pygame.Rect(0, 0, 110, 74)
            r.center = (x, y + 34)
            shadow(s, r)
            pygame.draw.rect(s, (168, 150, 136), r.move(0, 10), border_radius=8)
            pygame.draw.rect(s, (232, 220, 200), r, border_radius=8)
            pygame.draw.rect(s, (200, 186, 166), r.inflate(-20, -20), 3, border_radius=6)
    # notice board on the lobby wall, entrance at the bottom
    bx, by = layout.BOARD
    pygame.draw.rect(s, (110, 78, 54), (bx - 84, by - 126, 168, 60), border_radius=6)
    pygame.draw.rect(s, (176, 136, 96), (bx - 76, by - 120, 152, 48), border_radius=4)
    for i, c in enumerate(((244, 236, 214), (220, 236, 232), (250, 226, 170))):
        pygame.draw.rect(s, c, (bx - 66 + i * 48, by - 114, 38, 36))
        pygame.draw.circle(s, (190, 70, 60), (bx - 47 + i * 48, by - 110), 4)
    ex, _ = layout.ENTRANCE
    lobby = rooms["fuajee"]
    pygame.draw.rect(s, (150, 60, 50), (ex - 110, lobby.bottom - 70, 220, 64), border_radius=8)
    pygame.draw.rect(s, (236, 214, 176), (ex - 96, lobby.bottom - 60, 192, 44), 3, border_radius=6)
    pygame.draw.rect(s, (70, 48, 40), (ex - 90, lobby.bottom, 180, 40))
    pygame.draw.rect(s, (150, 104, 66), (ex - 84, lobby.bottom + 4, 82, 32), border_radius=4)
    pygame.draw.rect(s, (150, 104, 66), (ex + 2, lobby.bottom + 4, 82, 32), border_radius=4)
    grain(s, 60000, (255, 240, 220), (40, 20, 10), 12)
    save(s, "map.png")


# ---------------------------------------------------------------- record images

def blueprint(rec, variant):
    w, h = 800, 600
    blue, wh = (30, 66, 118), (228, 238, 250)
    s = pygame.Surface((w, h))
    s.fill(blue)
    for x in range(0, w, 40):
        pygame.draw.line(s, (48, 86, 140), (x, 0), (x, h))
    for y in range(0, h, 40):
        pygame.draw.line(s, (48, 86, 140), (0, y), (w, y))
    pygame.draw.rect(s, wh, (16, 16, w - 32, h - 32), 2)
    pygame.draw.line(s, wh, (60, 430), (740, 430), 3)
    if variant == "tsirkus":
        pygame.draw.rect(s, wh, (120, 280, 240, 150), 3)
        pygame.draw.polygon(s, wh, [(380, 430), (380, 300), (520, 180), (660, 300), (660, 430)], 3)
        pygame.draw.line(s, wh, (520, 180), (520, 130), 3)
        pygame.draw.polygon(s, wh, [(520, 130), (560, 142), (520, 154)], 3)
        pygame.draw.arc(s, wh, (480, 350, 80, 160), 0, math.pi, 3)
    elif variant == "tollakuur":
        pygame.draw.rect(s, wh, (180, 280, 440, 150), 3)
        pygame.draw.polygon(s, wh, [(160, 280), (400, 200), (640, 280)], 3)
        for x in (230, 420):
            pygame.draw.rect(s, wh, (x, 320, 150, 110), 3)
            pygame.draw.line(s, wh, (x, 320), (x + 150, 430), 2)
            pygame.draw.line(s, wh, (x + 150, 320), (x, 430), 2)
    else:
        floors = 2 if variant == "tubakavabrik" else 1
        top = 430 - floors * 110
        pygame.draw.rect(s, wh, (180, top, 440, floors * 110), 3)
        pygame.draw.polygon(s, wh, [(160, top), (640, top), (580, top - 70), (220, top - 70)], 3)
        for f in range(floors):
            for i in range(5):
                x, y = 206 + i * 82, top + 24 + f * 110
                if f == floors - 1 and i == 2:
                    pygame.draw.rect(s, wh, (x, y, 56, 86), 3)
                else:
                    pygame.draw.rect(s, wh, (x, y, 56, 60), 3)
                    pygame.draw.line(s, wh, (x + 28, y), (x + 28, y + 60), 2)
        if floors == 2:
            for cx in (300, 500):
                pygame.draw.rect(s, wh, (cx, top - 120, 30, 56), 3)
    pygame.draw.rect(s, wh, (420, 470, 350, 100), 2)
    label(s, rec["title"], (432, 480), "mono", 18, wh)
    y = 506
    for k, v in rec["given"][:3]:
        label(s, f"{k}: {v}", (432, y), "mono", 15, wh)
        y += 20
    label(s, "ASENDUSPILT – skaneering lisada", (40, 548), "mono", 15, (236, 170, 170))
    grain(s, 5000, alpha=10)
    return s


def document(rec):
    ink = (62, 44, 30)
    s = vgrad((800, 600), (240, 230, 206), (226, 212, 184))
    f = font("italic", 25)
    y = 56
    for line in rec["original"]:
        s.blit(f.render(line, True, ink), (48, y))
        y += 36
    label(s, f"{rec['given'][0][1]}, {rec['given'][1][1]} · ärakiri protokollist", (400, 566), "mono", 15, ink, center=True, alpha=200)
    grain(s, 6000, (255, 255, 255), (90, 60, 30), 16)
    return s


def make_record_images():
    with open("data/records.json", encoding="utf-8") as f:
        records = json.load(f)
    for rec in records:
        if rec["wing"] == "linn":
            save(blueprint(rec, rec["id"]), rec["image"])
        elif rec["wing"] == "vald":
            save(document(rec), rec["image"])


# ---------------------------------------------------------------- sound

RATE = 22050


def write_ogg(name, samples, peak=0.8):
    import soundfile
    os.makedirs(SND, exist_ok=True)
    m = max(1e-9, max(abs(v) for v in samples))
    k = peak * 32767 / m
    tmp = f"{SND}/_tmp.wav"
    with wave.open(tmp, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", int(v * k)) for v in samples))
    # the browser build only plays OGG
    data, rate = soundfile.read(tmp)
    soundfile.write(f"{SND}/{name}", data, rate, format="OGG", subtype="VORBIS")
    os.remove(tmp)
    print("wrote", f"{SND}/{name}")


def bell(freq, dur=1.6, decay=3.2):
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        env = math.exp(-decay * t) * min(1, t * 200)
        v = (math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 2.01 * t) * math.exp(-4 * t)
             + 0.15 * math.sin(2 * math.pi * freq * 3.02 * t) * math.exp(-7 * t))
        out.append(v * env)
    return out


def kalimba(freq, dur=3.0):
    """A soft plucked note for the background music."""
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        env = math.exp(-1.7 * t) * min(1, t * 90) * min(1, (dur - t) * 6)
        v = (math.sin(2 * math.pi * freq * t) + 0.22 * math.sin(2 * math.pi * freq * 2 * t) * math.exp(-5 * t)
             + 0.1 * math.sin(2 * math.pi * freq * 5.4 * t) * math.exp(-22 * t))
        out.append(v * env)
    return out


def mix(tracks, length):
    out = [0.0] * length
    for offset, tr in tracks:
        o = int(offset * RATE)
        for i, v in enumerate(tr):
            if o + i < length:
                out[o + i] += v
    return out


def make_sounds():
    for i, f in enumerate((440.0, 554.37, 659.25, 739.99, 880.0, 1108.73)):
        write_ogg(f"chime_{i}.ogg", bell(f), 0.5)
    # A major pentatonic over two octaves; the game plays these sparsely as music
    for i, f in enumerate((220.0, 246.94, 277.18, 329.63, 369.99, 440.0, 493.88, 554.37, 659.25)):
        write_ogg(f"note_{i}.ogg", kalimba(f), 0.5)
    write_ogg("place.ogg", bell(659.25, 0.7, 7), 0.45)
    n = int(RATE * 0.3)
    write_ogg("wrong.ogg", [math.sin(2 * math.pi * (196 - 40 * i / n) * i / RATE) * math.sin(math.pi * i / n) for i in range(n)], 0.3)
    arp = [(0.0, bell(440, 3, 1.6)), (0.22, bell(554.37, 3, 1.6)), (0.44, bell(659.25, 3, 1.6)), (0.72, bell(880, 3.2, 1.3))]
    write_ogg("restore.ogg", mix(arp, int(RATE * 4)), 0.6)
    n = int(RATE * 1.2)
    write_ogg("hum.ogg", [math.sin(2 * math.pi * (240 + 160 * (i / n) ** 2) * i / RATE) * math.sin(math.pi * i / n) ** 0.6 for i in range(n)], 0.14)
    n = int(RATE * 0.9)
    low, out = 0.0, []
    for i in range(n):
        k = i / n
        low += (0.02 + 0.25 * math.sin(math.pi * k)) * (rnd.uniform(-1, 1) - low)
        out.append(low * math.sin(math.pi * k))
    write_ogg("enter.ogg", out, 0.35)
    unlock = [(0.0, kalimba(329.63, 2)), (0.16, kalimba(440, 2)), (0.32, kalimba(554.37, 2)), (0.5, kalimba(659.25, 2.4))]
    write_ogg("unlock.ogg", mix(unlock, int(RATE * 3)), 0.6)


# ---------------------------------------------------------------- people and things for the trips

def person(name, coat, hat=None, hair=(70, 48, 36), small=False, skirt=False, beard=False):
    """A villager seen from a high angle, 72x100 with the feet at the bottom centre."""
    s = pygame.Surface((72, 100), pygame.SRCALPHA)
    k = 0.78 if small else 1.0
    cx, base = 36, 94
    sh = pygame.Surface((72, 100), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (20, 10, 10, 70), (cx - 22 * k, base - 12, 44 * k, 16))
    s.blit(sh, (0, 0))
    bw, bh = 40 * k, 50 * k
    body = pygame.Rect(cx - bw / 2, base - 8 - bh, bw, bh)
    if skirt:
        pygame.draw.polygon(s, coat, [(body.x + 6, body.y), (body.right - 6, body.y), (body.right + 4, body.bottom), (body.x - 4, body.bottom)])
        pygame.draw.rect(s, (240, 232, 214), (body.x + 8, body.y + bh * 0.45, bw - 16, bh * 0.5), border_radius=4)
    else:
        pygame.draw.rect(s, coat, body, border_radius=int(14 * k))
        pygame.draw.rect(s, shade(coat, 0.78), (body.x, body.bottom - bh * 0.3, bw, bh * 0.3), border_bottom_left_radius=int(14 * k), border_bottom_right_radius=int(14 * k))
        pygame.draw.line(s, shade(coat, 0.7), (cx, body.y + 10), (cx, body.bottom - 6), 2)
    for dx in (-1, 1):
        pygame.draw.circle(s, shade(coat, 0.9), (cx + dx * (bw / 2 + 1), body.y + bh * 0.42), 7 * k)
    hr = 16 * k
    hy = body.y - hr * 0.55
    pygame.draw.circle(s, (232, 196, 164), (cx, hy), hr)
    pygame.draw.circle(s, hair, (cx, hy - 3), hr, draw_top_left=True, draw_top_right=True)
    for dx in (-6, 6):
        pygame.draw.circle(s, (50, 36, 30), (cx + dx * k, hy + 3), 2)
    if beard:
        pygame.draw.circle(s, hair, (cx, hy + 6), hr * 0.8, draw_bottom_left=True, draw_bottom_right=True)
    if hat:
        pygame.draw.ellipse(s, shade(hat, 0.8), (cx - hr - 6, hy - hr * 0.7, (hr + 6) * 2, hr * 0.9))
        pygame.draw.ellipse(s, hat, (cx - hr * 0.75, hy - hr * 1.25, hr * 1.5, hr * 1.1))
    if skirt and not hat:
        pygame.draw.circle(s, hair, (cx + hr * 0.9, hy + hr * 0.7), 5 * k)
        pygame.draw.circle(s, hair, (cx - hr * 0.9, hy + hr * 0.7), 5 * k)
    save(s, f"npc/{name}.png")


def make_people():
    person("ado", (150, 84, 60), hair=(96, 60, 36), beard=True)
    person("harms", (60, 60, 76), hat=(40, 40, 50), hair=(200, 196, 190), beard=True)
    person("kohtumees_0", (96, 82, 66), hair=(60, 44, 34), beard=True)
    person("kohtumees_1", (84, 96, 80), hair=(190, 180, 170))
    person("kohtumees_2", (110, 90, 100), hair=(110, 70, 40), beard=True)
    person("kirjutaja", (70, 86, 110), hair=(60, 44, 34))
    person("peremees_0", (120, 100, 70), hat=(90, 70, 50), hair=(60, 44, 34), beard=True)
    person("peremees_1", (96, 110, 96), hat=(60, 56, 50), hair=(180, 170, 160), beard=True)
    person("peremees_2", (130, 96, 84), hat=(110, 90, 60), hair=(96, 60, 36))
    person("peremees_3", (90, 90, 110), hat=(70, 60, 60), hair=(60, 44, 34), beard=True)
    person("tydruk", (170, 80, 76), hair=(210, 170, 90), small=True, skirt=True)

    # the courtroom door: shut, and swung open
    for name, open_ in (("door_closed", False), ("door_open", True)):
        s = pygame.Surface((120, 110), pygame.SRCALPHA)
        if open_:
            pygame.draw.polygon(s, (120, 82, 52), [(8, 30), (22, 30), (22, 104), (8, 96)])
            pygame.draw.polygon(s, (90, 60, 40), [(8, 30), (22, 30), (22, 104), (8, 96)], 3)
        else:
            pygame.draw.rect(s, (130, 90, 56), (10, 34, 100, 46), border_radius=4)
            for x in range(30, 110, 22):
                pygame.draw.line(s, (96, 64, 42), (x, 36), (x, 78), 2)
            pygame.draw.rect(s, (90, 60, 40), (10, 34, 100, 46), 3, border_radius=4)
            pygame.draw.rect(s, (60, 56, 60), (50, 50, 34, 10), border_radius=4)
            pygame.draw.circle(s, (200, 170, 100), (84, 55), 6)
        save(s, f"obj/{name}.png")
    for name, lit in (("candle_off", False), ("candle_on", True)):
        s = pygame.Surface((90, 110), pygame.SRCALPHA)
        if lit:
            glow(s, (45, 44), 44, (255, 190, 90), 1.6)
            mask = pygame.Surface((90, 110), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), (45, 44), 44)
        pygame.draw.ellipse(s, (150, 130, 90), (30, 84, 30, 12))
        pygame.draw.rect(s, (244, 236, 214), (39, 52, 12, 36), border_radius=3)
        pygame.draw.line(s, (50, 40, 30), (45, 52), (45, 46), 2)
        if lit:
            pygame.draw.ellipse(s, (255, 200, 90), (38, 26, 14, 24))
            pygame.draw.ellipse(s, (255, 246, 210), (42, 34, 6, 12))
        save(s, f"obj/{name}.png")
    # keepsake: the scribe's quill
    s = pygame.Surface((80, 80), pygame.SRCALPHA)
    pygame.draw.polygon(s, (244, 240, 230), [(14, 66), (58, 8), (70, 14), (30, 60)])
    pygame.draw.line(s, (150, 140, 130), (12, 70), (64, 12), 3)
    pygame.draw.polygon(s, (60, 50, 60), [(8, 74), (16, 62), (20, 68)])
    save(s, "obj/keepsake_koiola.png")


def tree(s, x, y, r=70):
    sh = pygame.Rect(x - r, y - r * 0.3, r * 2, r * 1.1)
    shadow(s, sh, radius=int(r * 0.5), offset=(10, 18), alpha=60)
    pygame.draw.rect(s, (104, 72, 48), (x - 9, y - 10, 18, 40), border_radius=6)
    for i in range(11):
        a = i / 11 * math.tau
        d = rnd.uniform(0.25, 0.6) * r
        pygame.draw.circle(s, rnd.choice(((92, 140, 80), (108, 156, 86), (128, 160, 80), (190, 170, 80))),
                           (x + math.cos(a) * d, y - r * 0.5 + math.sin(a) * d * 0.8), rnd.uniform(0.38, 0.55) * r)
    pygame.draw.circle(s, (140, 176, 96), (x - r * 0.15, y - r * 0.7), r * 0.32)


def make_koiola_map():
    W, H = 2400, 1500
    s = pygame.Surface((W, H))
    s.fill((126, 150, 88))
    # grass: mottled late-summer greens and yellows
    for _ in range(5200):
        x, y = rnd.randrange(W), rnd.randrange(H)
        c = rnd.choice(((118, 144, 82), (136, 158, 92), (150, 164, 96), (166, 168, 92), (110, 136, 80)))
        pygame.draw.ellipse(s, c, (x, y, rnd.randint(30, 110), rnd.randint(14, 44)))
    for _ in range(2600):
        x, y = rnd.randrange(W), rnd.randrange(H)
        pygame.draw.line(s, (96, 124, 70), (x, y), (x + rnd.randint(-3, 3), y - rnd.randint(6, 12)), 2)
    for _ in range(260):
        x, y = rnd.randrange(W), rnd.randrange(H)
        pygame.draw.circle(s, rnd.choice(((250, 240, 200), (240, 200, 90), (230, 150, 150))), (x, y), 3)
    # dirt path from the gate to the door, and a worn patch in the yard
    path = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(760, 1500, 6):
        wob = math.sin(y / 90) * 26
        pygame.draw.ellipse(path, (190, 160, 112, 255), (1200 - 80 + wob, y - 30, 160, 70))
    pygame.draw.ellipse(path, (190, 160, 112, 255), (900, 760, 620, 190))
    pygame.draw.ellipse(path, (184, 154, 108, 255), (520, 960, 520, 260))
    path = pygame.transform.gaussian_blur(path, 10)
    s.blit(path, (0, 0))
    for _ in range(500):
        x, y = rnd.randrange(500, 1560), rnd.randrange(760, 1500)
        if path.get_at((x, y))[3] > 120:
            pygame.draw.circle(s, rnd.choice(((170, 142, 100), (204, 176, 128))), (x, y), rnd.randint(2, 4))

    # fence around the yard, gate at the bottom
    def fence(a, b):
        n = int(math.dist(a, b) / 46)
        for i in range(n + 1):
            x = a[0] + (b[0] - a[0]) * i / n
            y = a[1] + (b[1] - a[1]) * i / n
            pygame.draw.rect(s, (60, 44, 34), (x - 3, y - 4, 12, 40), border_radius=3)
            pygame.draw.rect(s, (150, 112, 76), (x - 5, y - 10, 12, 40), border_radius=3)
        for off in (0, 14):
            pygame.draw.line(s, (170, 130, 90), (a[0], a[1] + off), (b[0], b[1] + off), 6)
    fence((280, 130), (2120, 130))
    fence((280, 1400), (1100, 1400))
    fence((1300, 1400), (2120, 1400))
    for x in (280, 2120):
        fence((x, 130), (x, 1400))

    # the parish house: log walls, plank floor, seen without its roof
    outer = pygame.Rect(700, 200, 1000, 560)
    inner = pygame.Rect(740, 240, 920, 480)
    shadow(s, outer, radius=10, offset=(16, 26), alpha=90)
    pygame.draw.rect(s, (112, 78, 52), outer, border_radius=8)
    for y in range(outer.y + 6, outer.bottom, 13):
        pygame.draw.line(s, (88, 60, 40), (outer.x + 4, y), (outer.right - 4, y), 2)
    planks(s, inner, (196, 156, 110))
    for i in range(22):
        line = pygame.Surface((inner.w, 1), pygame.SRCALPHA)
        line.fill((40, 20, 10, int(80 * (1 - i / 22))))
        s.blit(line, (inner.x, inner.y + i))
    # doorway in the bottom wall, with a stone step
    planks(s, (1150, 720, 100, 40), (176, 136, 96))
    pygame.draw.rect(s, (170, 166, 158), (1130, 760, 140, 34), border_radius=8)
    pygame.draw.rect(s, (140, 136, 130), (1130, 782, 140, 12), border_radius=6)
    # windows in the side walls
    for wy in (360, 560):
        for wx in (700, 1660):
            pygame.draw.rect(s, (200, 220, 230), (wx + 8, wy, 24, 80))
            pygame.draw.line(s, (88, 60, 40), (wx + 8, wy + 40), (wx + 32, wy + 40), 3)
    # inside: rug, court table, chairs, scribe's desk, stove, bench, lamps
    prop(s, "rug", 1200, 520, 560, 200, (150, 70, 58))
    for cx in (1040, 1200, 1360):
        prop(s, "chair", cx, 330, 0, 0, (120, 60, 50))
    prop(s, "table", 1200, 400, 560, 92, (0, 0, 0))
    pygame.draw.rect(s, (244, 236, 214), (1170, 380, 66, 44))
    pygame.draw.rect(s, (120, 60, 50), (1166, 376, 74, 52), 4)
    prop(s, "desk", 1530, 600, 170, 100, (0, 0, 0))
    pygame.draw.rect(s, (250, 242, 220), (1480, 572, 84, 56), border_radius=3)
    pygame.draw.line(s, (120, 100, 80), (1522, 574), (1522, 626), 2)
    for ly in range(582, 622, 8):
        pygame.draw.line(s, (90, 70, 60), (1486, ly), (1516, ly), 2)
        pygame.draw.line(s, (90, 70, 60), (1528, ly), (1552 - rnd.randint(0, 14), ly), 2)
    prop(s, "chair", 1530, 680, 0, 0, (70, 86, 110))
    prop(s, "stove", 810, 310, 110, 110, (0, 0, 0))
    prop(s, "bench", 860, 640, 200, 46, (0, 0, 0))
    prop(s, "shelf", 1630, 380, 46, 200, (0, 0, 0))
    glow(s, (1200, 300), 260, (255, 200, 120), 0.5)

    # the yard: cart, hay, well, woodpile, trees
    cart = pygame.Rect(470, 1010, 200, 110)
    shadow(s, cart, offset=(10, 16))
    pygame.draw.rect(s, (150, 108, 70), cart, border_radius=8)
    pygame.draw.rect(s, (104, 72, 48), cart, 6, border_radius=8)
    for x in range(cart.x + 30, cart.right, 34):
        pygame.draw.line(s, (104, 72, 48), (x, cart.y + 6), (x, cart.bottom - 6), 3)
    for wx, wy in ((cart.x + 30, cart.y - 6), (cart.right - 30, cart.y - 6), (cart.x + 30, cart.bottom + 6), (cart.right - 30, cart.bottom + 6)):
        pygame.draw.ellipse(s, (70, 50, 40), (wx - 26, wy - 9, 52, 18))
    pygame.draw.line(s, (104, 72, 48), (cart.right, cart.centery - 20), (cart.right + 110, cart.centery - 30), 6)
    pygame.draw.line(s, (104, 72, 48), (cart.right, cart.centery + 20), (cart.right + 110, cart.centery + 30), 6)
    for hx, hy, hr in ((1880, 420, 90), (1960, 560, 70), (440, 380, 80)):
        shadow(s, pygame.Rect(hx - hr, hy - hr * 0.5, hr * 2, hr * 1.3), radius=hr, offset=(10, 16))
        pygame.draw.ellipse(s, (214, 184, 100), (hx - hr, hy - hr * 0.8, hr * 2, hr * 1.6))
        pygame.draw.ellipse(s, (234, 206, 124), (hx - hr * 0.7, hy - hr * 0.75, hr * 1.4, hr * 1.0))
        for _ in range(40):
            a = rnd.uniform(0, math.tau)
            px, py = hx + math.cos(a) * hr * 0.8, hy + math.sin(a) * hr * 0.6
            pygame.draw.line(s, (190, 160, 80), (px, py), (px + rnd.randint(-10, 10), py + rnd.randint(4, 14)), 2)
    well = pygame.Rect(1760, 980, 120, 120)
    shadow(s, well, radius=60, offset=(10, 16))
    pygame.draw.circle(s, (160, 156, 150), well.center, 60)
    pygame.draw.circle(s, (60, 80, 100), well.center, 42)
    pygame.draw.circle(s, (90, 120, 140), (well.centerx - 8, well.centery - 8), 16)
    pygame.draw.line(s, (104, 72, 48), (well.x - 10, well.centery), (well.right + 10, well.centery), 8)
    for i in range(6):
        for j in range(3 - i // 2):
            pygame.draw.ellipse(s, (150, 110, 74), (1840 + i * 34, 1240 - j * 22, 32, 24))
            pygame.draw.ellipse(s, (210, 176, 130), (1846 + i * 34, 1244 - j * 22, 20, 14))
    for tx, ty, r in ((360, 260, 86), (2030, 250, 90), (2040, 1280, 80), (380, 1300, 74), (160, 700, 90), (2260, 760, 96),
                      (1200, 80, 70), (700, 60, 60), (1740, 70, 64), (140, 220, 70), (2280, 300, 70), (150, 1260, 80), (2270, 1250, 76)):
        tree(s, tx, ty, r)
    grain(s, 50000, (255, 250, 220), (30, 40, 10), 12)
    save(s, "maps/koiola.png")


if __name__ == "__main__":
    make_ghost()
    make_small()
    make_people()
    make_koiola_map()
    make_map()
    make_record_images()
    make_sounds()
