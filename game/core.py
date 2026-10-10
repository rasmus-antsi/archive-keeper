"""Shared settings, asset loading, text and small effects."""
import json
import math
import random

import pygame

W, H = 1280, 720
ART_W = 1920            # art and data coordinates are authored at 1920x1080
S = W / ART_W
FPS = 60
WAIT = 9999.0         # a text box hold that means: stay until a key is pressed

CREAM = (240, 232, 212)
INK = (52, 40, 34)
TEAL = (130, 226, 214)
WARM = (255, 206, 130)
DIM = (150, 160, 176)

_FONT_FILES = {
    "serif": "CrimsonText-Regular.ttf",
    "italic": "CrimsonText-Italic.ttf",
    "bold": "CrimsonText-SemiBold.ttf",
    "mono": "CourierPrime-Regular.ttf",
}
_fonts, _images, _sounds, _texts, _glows = {}, {}, {}, {}, {}


def art(p):
    """Art-space point (1920x1080) to screen space."""
    return pygame.Vector2(p[0] * S, p[1] * S)


def font(kind, size):
    key = (kind, size)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(f"assets/fonts/{_FONT_FILES[kind]}", size)
    return _fonts[key]


def image(name, scale=S):
    key = (name, scale)
    if key not in _images:
        try:
            surf = pygame.image.load(f"assets/img/{name}").convert_alpha()
        except (FileNotFoundError, pygame.error):
            # missing art shows up as a labelled box instead of crashing
            surf = pygame.Surface((240, 240), pygame.SRCALPHA)
            surf.fill((200, 60, 120, 160))
            surf.blit(font("mono", 20).render(name, True, (255, 255, 255)), (8, 8))
        if scale != 1:
            size = (max(1, round(surf.get_width() * scale)), max(1, round(surf.get_height() * scale)))
            surf = pygame.transform.smoothscale(surf, size)
        _images[key] = surf
    return _images[key]


def sound(name):
    if name not in _sounds:
        try:
            _sounds[name] = pygame.mixer.Sound(f"assets/snd/{name}")
        except (FileNotFoundError, pygame.error):
            _sounds[name] = None
    return _sounds[name]


def play(name, volume=1.0, loops=0):
    snd = sound(name)
    if snd:
        snd.set_volume(volume)
        snd.play(loops=loops)
    return snd


def stop(name):
    snd = _sounds.get(name)
    if snd:
        snd.fadeout(250)


def load_records():
    with open("data/records.json", encoding="utf-8") as f:
        return json.load(f)


def text(string, kind="serif", size=28, color=CREAM):
    key = (string, kind, size, color)
    if key not in _texts:
        if len(_texts) > 600:
            _texts.clear()
        _texts[key] = font(kind, size).render(string, True, color)
    return _texts[key]


def wrap(string, kind, size, width):
    f = font(kind, size)
    lines = []
    for para in string.split("\n"):
        line = ""
        for word in para.split(" "):
            trial = f"{line} {word}".strip()
            if f.size(trial)[0] <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def draw_text(surf, string, pos, kind="serif", size=28, color=CREAM, center=False, alpha=255):
    img = text(string, kind, size, color)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)
    return rect


def draw_wrapped(surf, string, pos, width, kind="serif", size=28, color=CREAM, line_gap=6, center=False):
    x, y = pos
    for line in wrap(string, kind, size, width):
        img = text(line, kind, size, color)
        surf.blit(img, (x + (width - img.get_width()) // 2 if center else x, y))
        y += img.get_height() + line_gap
    return y


def glow(radius, color):
    """A cached soft radial light, drawn with additive blending."""
    key = (radius, color)
    if key not in _glows:
        small = pygame.Surface((64, 64), pygame.SRCALPHA)
        for i in range(32, 0, -1):
            k = 1 - i / 32
            pygame.draw.circle(small, (*[round(c * k * k) for c in color], 255), (32, 32), i)
        _glows[key] = pygame.transform.smoothscale(small, (radius * 2, radius * 2))
    return _glows[key]


def add_glow(surf, pos, radius, color, k=1.0):
    # radius and brightness are quantised so the cache stays small
    radius = max(4, int(radius) // 4 * 4)
    k = round(max(0.0, min(1.0, k)) * 8) / 8
    if k == 0:
        return
    color = tuple(int(c * k) for c in color)
    surf.blit(glow(radius, color), (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGB_ADD)


def panel(size, color=(18, 22, 34), alpha=215, radius=16):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, alpha), (0, 0, *size), border_radius=radius)
    return surf


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def pressed_confirm(events):
    for e in events:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e):
            return True
    return False


def clicked(events):
    for e in events:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            return pygame.Vector2(e.pos)
    return None


def pressed(events, *keys):
    return any(e.type == pygame.KEYDOWN and e.key in keys for e in events)


class Motes:
    """Slow drifting dust; makes still scenes feel alive."""

    def __init__(self, count=36, color=(255, 240, 210)):
        self.color = color
        self.items = [[random.uniform(0, W), random.uniform(0, H), random.uniform(4, 12),
                       random.uniform(0, 6.28), random.uniform(1.5, 3.5)] for _ in range(count)]

    def update(self, dt):
        for m in self.items:
            m[3] += dt * 0.5
            m[0] = (m[0] + math.cos(m[3]) * m[2] * dt) % W
            m[1] = (m[1] - m[2] * dt * 0.6) % H

    def draw(self, surf):
        for x, y, _, phase, size in self.items:
            add_glow(surf, (x, y), size * 4, self.color, 0.25 + 0.2 * math.sin(phase * 2))


class TextBox:
    """One line at the bottom of the screen, typed out, never blocking."""

    def __init__(self):
        self.string = ""
        self.speaker = ""
        self.shown = 0.0
        self.age = 0.0
        self.hold = 0.0

    def say(self, string, speaker="", hold=7.0):
        self.string, self.speaker = string, speaker
        self.shown, self.age, self.hold = 0.0, 0.0, hold

    def clear(self):
        self.string = ""

    def update(self, dt):
        if not self.string:
            return
        self.shown += dt * 46
        if self.shown >= len(self.string):
            self.age += dt
            if self.age > self.hold:
                self.string = ""

    def draw(self, surf):
        if not self.string:
            return
        width = 860
        lines = wrap(self.string, "serif", 27, width - 56)
        height = 34 + len(lines) * 33 + (26 if self.speaker else 0)
        fade = 1.0 if self.age < self.hold - 0.6 else max(0.0, (self.hold - self.age) / 0.6)
        box = panel((width, height), alpha=int(215 * fade))
        x, y = (W - width) // 2, H - height - 28
        surf.blit(box, (x, y))
        ty = y + 16
        if self.speaker:
            draw_text(surf, self.speaker, (x + 28, ty), "mono", 17, TEAL, alpha=int(255 * fade))
            ty += 26
        left = int(self.shown)
        for line in lines:
            part = line[:max(0, left)]
            left -= len(line) + 1
            if part:
                draw_text(surf, part, (x + 28, ty), "serif", 27, CREAM, alpha=int(255 * fade))
            ty += 33
        if self.hold >= WAIT and self.shown >= len(self.string):
            draw_text(surf, "tühik >", (x + width - 96, y + height - 26), "mono", 14, WARM,
                      alpha=int(170 + 80 * math.sin(pygame.time.get_ticks() / 160)))


class Hotspot:
    """A place the ghost remembers by staying near it."""

    def __init__(self, pos, radius, data=None, repeat=False, linger=1.2):
        self.linger = linger
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.data = data or {}
        self.repeat = repeat
        self.fill = 0.0
        self.done = False
        self.inside = False
        self.phase = random.uniform(0, 6.28)

    def update(self, dt, ghost_pos):
        """Returns True on the frame the linger completes."""
        was_inside = self.inside
        self.inside = self.pos.distance_to(ghost_pos) < self.radius
        self.phase += dt
        if self.done:
            if self.repeat and not self.inside:
                self.done, self.fill = False, 0.0
            return False
        if self.inside:
            if not was_inside:
                play("hum.ogg", 0.5)
            self.fill += dt / self.linger
            if self.fill >= 1:
                self.fill, self.done = 1.0, True
                return True
        else:
            if was_inside:
                stop("hum.ogg")
            self.fill = max(0.0, self.fill - dt * 0.9)
        return False

    def draw(self, surf, color=TEAL, cam=(0, 0)):
        if self.done and not self.repeat:
            return
        pos = (self.pos.x - cam[0], self.pos.y - cam[1] + math.sin(self.phase * 1.7) * 4)
        pulse = 0.5 + 0.5 * math.sin(self.phase * 2.4)
        r = int(18 + 8 * pulse + 30 * self.fill)
        add_glow(surf, pos, r, color, 0.55 + 0.3 * pulse)
        pygame.draw.circle(surf, color, pos, 4)
        if self.fill > 0:
            rect = pygame.Rect(0, 0, 64, 64)
            rect.center = pos
            pygame.draw.arc(surf, CREAM, rect, math.pi / 2 - self.fill * math.tau, math.pi / 2, 4)
