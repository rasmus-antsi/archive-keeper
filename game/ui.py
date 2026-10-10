"""Text, panels, input helpers and the dialogue box. Sizes are for the 1920x1080 screen."""
import math

import pygame

from . import assets, settings

_texts, _wraps, _panels = {}, {}, {}

CONFIRM = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e)
BACK = (pygame.K_ESCAPE, pygame.K_BACKSPACE)


# ---------------------------------------------------------------- input

def pressed(events, *keys):
    return any(e.type == pygame.KEYDOWN and e.key in keys for e in events)


def confirm(events):
    return pressed(events, *CONFIRM)


def clicked(events):
    """Window position of a left click this frame, or None."""
    for e in events:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            return e.pos
    return None


# ---------------------------------------------------------------- text

def text(string, role="body", size=24, color=settings.CREAM):
    key = (string, role, size, color)
    if key not in _texts:
        if len(_texts) > 800:
            _texts.clear()
        _texts[key] = assets.font(role, size).render(string, True, color)
    return _texts[key]


def wrap(string, role, size, width):
    key = (string, role, size, width)
    if key in _wraps:
        return _wraps[key]
    if len(_wraps) > 400:
        _wraps.clear()
    f = assets.font(role, size)
    lines = _wraps[key] = []
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


def draw_text(surf, string, pos, role="body", size=24, color=settings.CREAM, center=False, alpha=255):
    img = text(string, role, size, color)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(max(0, alpha))
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)
    return rect


def draw_wrapped(surf, string, pos, width, role="body", size=24, color=settings.CREAM, gap=4, center=False, limit=None):
    """Draws wrapped lines and returns the y below the last one. limit caps the number of lines."""
    x, y = pos
    lines = wrap(string, role, size, width)
    if limit is not None and len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1].rstrip(" .,;") + " …"
    for line in lines:
        img = text(line, role, size, color)
        surf.blit(img, (x + (width - img.get_width()) // 2 if center else x, y))
        y += img.get_height() + gap
    return y


def draw_typed(surf, lines, shown, pos, role="body", size=24, color=settings.CREAM, step=None):
    """Already wrapped lines with only the first `shown` characters visible. Each line is
    rendered once and uncovered from the left, so typing costs nothing and words never jump."""
    x, y = pos
    f = assets.font(role, size)
    for line in lines:
        if shown <= 0:
            break
        img = text(line, role, size, color)
        if shown >= len(line):
            surf.blit(img, (x, y))
        else:
            surf.blit(img, (x, y), (0, 0, f.size(line[:int(shown)])[0], img.get_height()))
        shown -= len(line) + 1
        y += step or img.get_height() + 4
    return y


def key_prompt(surf, pos, key="E"):
    """A small bobbing key cap above something that can be used. pos is its top centre."""
    x, y = pos[0], pos[1] - 64 + round(math.sin(pygame.time.get_ticks() / 220) * 5)
    rect = pygame.Rect(0, 0, 54, 54)
    rect.midbottom = (x, y)
    pygame.draw.rect(surf, settings.NIGHT, rect.move(0, 5), border_radius=10)
    pygame.draw.rect(surf, settings.CREAM, rect, border_radius=10)
    draw_text(surf, key, rect.center, "mono", 34, settings.INK, center=True)


def pointer(surf, target, color=settings.TEAL):
    """An arrow at the edge of the screen towards something that is out of sight."""
    box = pygame.Rect(70, 110, settings.W - 140, settings.H - 240)
    if box.collidepoint(target):
        return
    centre = pygame.Vector2(box.center)
    way = pygame.Vector2(target) - centre
    k = min(box.w / 2 / abs(way.x) if way.x else 1e9, box.h / 2 / abs(way.y) if way.y else 1e9)
    tip = centre + way * k
    way = way.normalize()
    side = pygame.Vector2(-way.y, way.x)
    back = tip - way * (44 + 8 * math.sin(pygame.time.get_ticks() / 180))
    tip = back + way * 40
    pygame.draw.polygon(surf, settings.NIGHT, [tip + way * 8, back + side * 30 - way * 6, back - side * 30 - way * 6])
    pygame.draw.polygon(surf, color, [tip, back + side * 22, back - side * 22])


def panel(surf, rect, color=settings.NIGHT, alpha=225, radius=14, border=None):
    rect = pygame.Rect(rect)
    key = (rect.size, tuple(color), alpha, radius, tuple(border) if border else None)
    if key not in _panels:        # built once: making a see-through surface every frame is slow
        if len(_panels) > 60:
            _panels.clear()
        box = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (*color, alpha), box.get_rect(), border_radius=radius)
        if border:
            pygame.draw.rect(box, border, box.get_rect(), 3, border_radius=radius)
        _panels[key] = box
    surf.blit(_panels[key], rect)


def hint(surf, string, alpha=255):
    """One line of key help along the bottom edge."""
    width = text(string, "mono", 24, settings.CREAM).get_width() + 60
    panel(surf, (settings.W / 2 - width / 2, settings.H - 54, width, 46), alpha=170, radius=10)
    draw_text(surf, string, (settings.W / 2, settings.H - 31), "mono", 24, settings.CREAM, center=True, alpha=alpha)


def blink(speed=160):
    return int(170 + 80 * math.sin(pygame.time.get_ticks() / speed))


# ---------------------------------------------------------------- dialogue

class DialogueBox:
    """A queue of spoken lines, typed out one at a time; each waits for a key or click."""

    def __init__(self, x=180, width=settings.W - 360, top=False):
        self.x, self.width = x, width
        self.top = top           # sit at the top of the screen, when the speaker stands at the bottom
        self.queue = []          # (speaker, text)
        self.shown = 0.0
        self.on_done = None

    @property
    def active(self):
        return bool(self.queue)

    @property
    def talking(self):
        """The name of whoever is in the middle of a line, or None once it is fully typed."""
        if self.queue and self.shown < len(self.queue[0][1]):
            return self.queue[0][0]
        return None

    def say(self, lines, speaker="", on_done=None):
        """Queue one string or a list of them. on_done runs after the last line is dismissed."""
        if isinstance(lines, str):
            lines = [lines]
        if not self.queue:
            self.shown = 0.0
        self.queue += [(speaker, line) for line in lines]
        if on_done:
            self.on_done = on_done

    def update(self, dt, events):
        """Returns True while it is using the input, so the scene should ignore it."""
        if not self.queue:
            return False
        line = self.queue[0][1]
        self.shown += dt * 48
        if confirm(events) or clicked(events):
            if self.shown < len(line):
                self.shown = len(line)
            else:
                self.queue.pop(0)
                self.shown = 0.0
                if not self.queue and self.on_done:
                    done, self.on_done = self.on_done, None
                    done()
        return True

    def draw(self, surf):
        if not self.queue:
            return
        speaker, line = self.queue[0]
        x, width = self.x, self.width
        lines = wrap(line, "body", 44, width - 100)
        height = 56 + len(lines) * 54 + (44 if speaker else 0)
        y = 40 if self.top else settings.H - height - 70
        panel(surf, (x, y, width, height), radius=16, border=(70, 70, 84))
        ty = y + 24
        if speaker:
            draw_text(surf, speaker, (x + 50, ty), "mono", 26, settings.TEAL)
            ty += 44
        draw_typed(surf, lines, self.shown, (x + 50, ty), "body", 44, step=54)
        if self.shown >= len(line):
            draw_text(surf, "space >", (x + width - 150, y + height + 8), "mono", 22, settings.WARM, alpha=blink())
