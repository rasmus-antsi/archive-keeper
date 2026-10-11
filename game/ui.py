"""Text, panels, input helpers, menus and the dialogue box. Sizes are for the 1920x1080 screen."""
import math

import pygame

from . import assets, settings

_texts, _wraps, _panels = {}, {}, {}
_toast = ["", 0]           # the short message at the top of the screen, and when it goes (in get_ticks time)

CONFIRM = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e)
BACK = (pygame.K_ESCAPE, pygame.K_BACKSPACE)
UP, DOWN = (pygame.K_UP, pygame.K_w), (pygame.K_DOWN, pygame.K_s)
LEFT, RIGHT = (pygame.K_LEFT, pygame.K_a), (pygame.K_RIGHT, pygame.K_d)


# ---------------------------------------------------------------- input

def pressed(events, *keys):
    return any(e.type == pygame.KEYDOWN and e.key in keys for e in events)


def confirm(events):
    return pressed(events, *CONFIRM)


def clicked(events):
    """Game position of a left click this frame, or None."""
    for e in events:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            return e.pos
    return None


def pointed(events):
    """Game position the mouse moved to this frame, or None if it did not move."""
    for e in reversed(events):
        if e.type == pygame.MOUSEMOTION:
            return e.pos
    return None


class Repeat:
    """Turns a held key into steps: one at once, a short wait, then a steady run.
    Lists and sliders use it so that holding a key down scrolls."""

    def __init__(self, wait=0.34, every=0.06):
        self.wait, self.every = wait, every
        self.way = 0            # -1 or +1 while a key is held
        self.left = 0.0         # seconds until the next step

    def steps(self, dt, events, back, forth):
        """How many steps to take this frame; back and forth are tuples of keys."""
        taps = [1 if e.key in forth else -1 for e in events if e.type == pygame.KEYDOWN and e.key in back + forth]
        if taps:
            self.way, self.left = taps[-1], self.wait
            return sum(taps)
        if not self.way:
            return 0
        held = pygame.key.get_pressed()
        if not any(held[k] for k in (back if self.way < 0 else forth)):
            self.way = 0
            return 0
        self.left -= dt
        count = 0
        while self.left <= 0:
            self.left += self.every
            count += self.way
        return count


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


def _blit(surf, img, pos, alpha):
    """Draw a cached picture, see-through if asked, without making a copy of it."""
    if alpha >= 255:
        surf.blit(img, pos)
    elif alpha > 0:
        img.set_alpha(alpha)
        surf.blit(img, pos)
        img.set_alpha(255)


def draw_text(surf, string, pos, role="body", size=24, color=settings.CREAM, center=False, alpha=255):
    img = text(string, role, size, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    _blit(surf, img, rect, alpha)
    return rect


def draw_wrapped(surf, string, pos, width, role="body", size=24, color=settings.CREAM, gap=4, center=False, limit=None,
                 alpha=255):
    """Draws wrapped lines and returns the y below the last one. limit caps the number of lines."""
    x, y = pos
    lines = wrap(string, role, size, width)
    if limit is not None and len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1].rstrip(" .,;") + " …"
    for line in lines:
        img = text(line, role, size, color)
        _blit(surf, img, (x + (width - img.get_width()) // 2 if center else x, y), alpha)
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


def fit(string, role, size, width):
    """The string, cut short with an ellipsis if it is wider than width."""
    f = assets.font(role, size)
    if f.size(string)[0] <= width:
        return string
    while len(string) > 1 and f.size(string + "…")[0] > width:
        string = string[:-1].rstrip()
    return string + "…"


# ---------------------------------------------------------------- small parts

def panel(surf, rect, color=settings.NIGHT, alpha=225, radius=14, border=None):
    """A rounded plate, see-through as a whole. Built once and kept. The corners are cut
    with a reserved colour rather than per-pixel alpha, which is what keeps it cheap."""
    rect = pygame.Rect(rect)
    key = (rect.size, tuple(color), alpha, radius, tuple(border) if border else None)
    if key not in _panels:
        if len(_panels) > 60:
            _panels.clear()
        box = pygame.Surface(rect.size).convert()
        box.fill(assets.KEY)
        box.set_colorkey(assets.KEY, pygame.RLEACCEL)
        pygame.draw.rect(box, color, box.get_rect(), border_radius=radius)
        if border:
            pygame.draw.rect(box, border, box.get_rect(), 3, border_radius=radius)
        if alpha < 255:
            box.set_alpha(alpha, pygame.RLEACCEL)
        _panels[key] = box
    surf.blit(_panels[key], rect)


def key_prompt(surf, pos, key="E"):
    """A small bobbing key cap above something that can be used. pos is its top centre.
    It stays on the screen even when the thing itself is at the very top."""
    cap = _panels.get(("key", key))
    if cap is None:
        cap = _panels[("key", key)] = pygame.Surface((54, 59), pygame.SRCALPHA)
        pygame.draw.rect(cap, settings.NIGHT, (0, 5, 54, 54), border_radius=10)
        pygame.draw.rect(cap, settings.CREAM, (0, 0, 54, 54), border_radius=10)
        label = text(key, "pixel", 34, settings.INK)
        cap.blit(label, label.get_rect(center=(27, 27)))
    bob = round(math.sin(pygame.time.get_ticks() / 220) * 5)
    x = max(40, min(settings.W - 40, pos[0]))
    y = max(74, min(settings.H - 130, pos[1] - 18))
    surf.blit(cap, (x - 27, y - 54 + bob))


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


def hint(surf, string):
    """One line of key help along the bottom edge."""
    width = text(string, "pixel", 24, settings.CREAM).get_width() + 60
    panel(surf, (settings.W / 2 - width / 2, settings.H - 54, width, 46), alpha=170, radius=10)
    draw_text(surf, string, (settings.W / 2, settings.H - 31), "pixel", 24, settings.CREAM, center=True)


def label(surf, string, pos, role="pixel", size=26, color=settings.CREAM, alpha=150):
    """A line of text on a dark plate that is as wide as the text. pos is the plate's top left."""
    img = text(string, role, size, color)
    panel(surf, (pos[0], pos[1], img.get_width() + 32, img.get_height() + 22), alpha=alpha)
    surf.blit(img, (pos[0] + 16, pos[1] + 11))


def blink(speed=160):
    return int(170 + 80 * math.sin(pygame.time.get_ticks() / speed))


def toast(string, seconds=1.6):
    """Show a short message at the top of the screen for a moment (see draw_toast)."""
    _toast[:] = [string, pygame.time.get_ticks() + int(seconds * 1000)]


def draw_toast(surf):
    left = _toast[1] - pygame.time.get_ticks()
    if left <= 0:
        return
    alpha = min(255, left * 255 // 300) // 51 * 51          # fades out over its last 0.3 seconds, in five steps
    img = text(_toast[0], "pixel", 26, settings.WARM)
    plate = pygame.Rect(0, 84, img.get_width() + 52, 50)
    plate.centerx = settings.W // 2
    panel(surf, plate, alpha=alpha * 200 // 255, radius=10)
    _blit(surf, img, img.get_rect(center=plate.center), alpha)


# ---------------------------------------------------------------- menus

class Choice:
    """One row of a Menu.

    label   the text, or a function that returns it (for rows that show a setting)
    pick    what Enter or a click does
    level   for a slider row: a function returning how full it is, 0..1
    change  for a slider row: called with the new level, 0..1
    """

    def __init__(self, label, pick=None, level=None, change=None):
        self.label, self.pick, self.level, self.change = label, pick, level, change

    @property
    def caption(self):
        return self.label() if callable(self.label) else self.label


class Menu:
    """A column of choices, worked with W/S or the arrows and Enter, or with the mouse.
    Holding a key down keeps moving; the highlight glides from row to row."""
    ROW = 66
    NOTCHES = 10

    def __init__(self, choices, top_centre, width=620):
        self.choices = choices
        self.x, self.y = top_centre          # middle of the first row's top edge
        self.width = width
        self.cursor = 0
        self.glide = 0.0                     # where the highlight is drawn; it runs after the cursor
        self.rows, self.slides = Repeat(), Repeat(every=0.05)

    @property
    def height(self):
        return len(self.choices) * self.ROW

    def row(self, i):
        return pygame.Rect(self.x - self.width // 2, self.y + i * self.ROW, self.width, self.ROW - 8)

    def bar(self, i):
        """The part of a slider row that fills up."""
        row = self.row(i)
        return pygame.Rect(row.right - 284, row.centery - 9, 260, 18)

    def move(self, step):
        if step:
            self.cursor = (self.cursor + step) % len(self.choices)
            assets.play("tick.ogg", 0.5)

    def update(self, dt, events):
        self.move(self.rows.steps(dt, events, UP, DOWN))
        over = pointed(events)
        click = clicked(events)
        for i in range(len(self.choices)):
            if over and self.row(i).collidepoint(over) and i != self.cursor:
                self.cursor = i
                assets.play("tick.ogg", 0.35)
            if click and self.row(i).collidepoint(click):
                self.cursor = i
        choice = self.choices[self.cursor]
        if choice.level:
            nudge = self.slides.steps(dt, events, LEFT, RIGHT)
            if nudge:
                self.slide(choice, round(choice.level() * self.NOTCHES) + nudge)
            bar = self.bar(self.cursor).inflate(24, 40)
            if click and bar.collidepoint(click):
                self.slide(choice, round((click[0] - bar.x - 12) / (bar.w - 24) * self.NOTCHES))
        elif choice.pick and (confirm(events) or (click and self.row(self.cursor).collidepoint(click))):
            choice.pick()
        self.glide += (self.cursor - self.glide) * (1 - math.exp(-28 * dt))

    def slide(self, choice, notch):
        notch = max(0, min(self.NOTCHES, notch))
        if notch != round(choice.level() * self.NOTCHES):
            choice.change(notch / self.NOTCHES)
            assets.play("tick.ogg", 0.5)

    def draw(self, surf):
        mark = self.row(0).move(0, round(self.glide * self.ROW))
        panel(surf, mark, (70, 58, 50), 235, radius=12, border=(132, 108, 80))
        for i, choice in enumerate(self.choices):
            row = self.row(i)
            chosen = i == self.cursor
            color = settings.CREAM if chosen else settings.DIM
            if not choice.level:
                draw_text(surf, choice.caption, row.center, "pixel", 34, color, center=True)
                continue
            img = text(choice.caption, "pixel", 34, color)
            surf.blit(img, (row.x + 28, row.centery - img.get_height() // 2))
            bar = self.bar(i)
            full = round(choice.level() * self.NOTCHES)
            for n in range(self.NOTCHES):
                notch = pygame.Rect(bar.x + n * 26, bar.y, 20, bar.h)
                lit = (settings.WARM if chosen else settings.DIM) if n < full else (58, 52, 56)
                pygame.draw.rect(surf, lit, notch, border_radius=4)


# ---------------------------------------------------------------- dialogue

class DialogueBox:
    """A queue of spoken lines, typed out one at a time; each waits for a key or click."""
    SPEED = 48           # characters a second
    RESTS = {".": 7, "!": 7, "?": 7, "…": 7, ",": 3, ";": 3, ":": 3}      # extra characters' worth of pause after these

    def __init__(self, x=180, width=settings.W - 360, top=False, prompt="space >"):
        self.x, self.width = x, width
        self.top = top           # sit at the top of the screen, when the speaker stands at the bottom
        self.prompt = prompt     # shown under a finished line
        self.queue = []          # (speaker, text)
        self.shown = 0.0
        self.rest = 0.0          # a breath after a comma or a full stop, counted in characters
        self.rise = 0.0          # 0..1: the box slides up into place when it first appears
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
            self.shown = self.rest = self.rise = 0.0
        self.queue += [(speaker, line) for line in lines]
        if on_done:
            self.on_done = on_done

    def update(self, dt, events):
        """Returns True while it is using the input, so the scene should ignore it."""
        if not self.queue:
            return False
        line = self.queue[0][1]
        self.rise = min(1.0, self.rise + dt / 0.16)
        self._type(line, dt * self.SPEED)
        if confirm(events) or clicked(events):
            if self.shown < len(line):
                self.shown, self.rest = float(len(line)), 0.0
            else:
                self.queue.pop(0)
                self.shown = self.rest = 0.0
                if not self.queue and self.on_done:
                    done, self.on_done = self.on_done, None
                    done()
        return True

    def _type(self, line, budget):
        """Uncover `budget` more characters; after a comma or a full stop, spend some of it
        on a breath instead."""
        while budget > 0 and self.shown < len(line):
            if self.rest > 0:
                spent = min(self.rest, budget)
                self.rest -= spent
                budget -= spent
                continue
            count = int(self.shown) + 1                  # the next whole number of characters
            if budget < count - self.shown:
                self.shown += budget
                return
            budget -= count - self.shown
            self.shown = float(count)
            if count < len(line) and line[count] == " ":
                self.rest = self.RESTS.get(line[count - 1], 0)

    def draw(self, surf):
        if not self.queue:
            return
        speaker, line = self.queue[0]
        x, width = self.x, self.width
        lines = wrap(line, "pixel", 44, width - 100)
        height = 56 + len(lines) * 54 + (44 if speaker else 0)
        slip = round((1 - self.rise) ** 2 * 36)          # eases into place
        y = 40 - slip if self.top else settings.H - height - 70 + slip
        panel(surf, (x, y, width, height), radius=16, border=(70, 70, 84))
        ty = y + 24
        if speaker:
            draw_text(surf, speaker, (x + 50, ty), "pixel", 26, settings.TEAL)
            ty += 44
        draw_typed(surf, lines, self.shown, (x + 50, ty), "pixel", 44, step=54)
        if self.shown >= len(line):
            draw_text(surf, self.prompt, (x + width - 150, y + height + 8), "pixel", 22, settings.WARM, alpha=blink())
