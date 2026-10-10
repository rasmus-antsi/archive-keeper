"""A place the ghost walks around in, larger than the screen: rooms, doorways, furniture,
roofs, lamplight and the camera that follows the ghost.

Everything here is measured in art pixels, the pixels the artists draw. The world is
drawn small (settings.VIEW, 240x135) and enlarged settings.PIXEL times onto the
screen in one step, which keeps it crisp and fast in the browser.

A map is a dict (see data/game.json "map" and data/documents/*.json "map"):

  size        [w, h] of the whole place
  ambient     [r, g, b] darkness; leave out for daylight
  background  optional painted picture of the whole place, size x size art pixels.
              With it nothing is painted in code and props are only drawn when
              they name a "sprite".
  rooms       painted in order, later ones on top:
              {"rect", "floor", "wall" (leave out for outdoors), "roof" (houses)}
  doors       [{"rect"}] openings the ghost can walk through walls in
  props       [{"type", "pos", ...}] furniture; "pos" is the top left of its picture.
              assets/img/props/<type>.png replaces the stand-in for a type, and
              "sprite" names a picture for one prop.
"""
import math

import pygame

from . import assets, paint, settings

VIEW = pygame.Rect(0, 0, settings.VIEW_W, settings.VIEW_H)
REACH = 9                      # how close to a thing counts as standing at it
_glows, _shadows = {}, {}


class Room:
    def __init__(self, data):
        self.data = data
        self.rect = pygame.Rect(data["rect"])
        self.wall = data.get("wall")
        self.wall_h = data.get("wall_h", 28) if self.wall else 0
        edge = 2 if self.wall else 0
        self.floor = pygame.Rect(self.rect.x + edge, self.rect.y + self.wall_h, self.rect.w - 2 * edge,
                                 self.rect.h - self.wall_h - edge)
        self.roof = None           # a picture drawn over the room while the ghost is outside it
        self.cover = 1.0           # how solid the roof is right now


class Prop:
    def __init__(self, data, painted):
        self.data = data
        self.type = data["type"]
        self.id = data.get("id")
        spec = paint.PROPS[self.type]
        self.flat, self.wall = spec.flat, spec.wall
        name = data.get("sprite") or f"props/{self.type}.png"
        self.image = assets.optional(name)
        if self.image is None and not painted:
            self.image = paint.make(data).convert_alpha()
        size = self.image.get_size() if self.image else data.get("size", spec.size)
        self.rect = pygame.Rect(data["pos"], size)
        depth = data.get("depth", spec.depth)
        self.solid = pygame.Rect(self.rect.x + spec.inset, self.rect.bottom - depth, self.rect.w - 2 * spec.inset,
                                 depth) if depth else None
        self.base = self.rect.top if self.wall else self.rect.bottom      # what it is sorted by
        light = data.get("light", spec.light)
        self.light = (self.rect.centerx, self.rect.top + 4, light[0], tuple(light[1])) if light else None

    @property
    def label(self):
        return self.data.get("label", self.type)

    def reach(self):
        return (self.solid or self.rect).inflate(REACH * 2, REACH * 2)


class World:
    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.size = tuple(data["size"])
        self.ambient = tuple(data["ambient"]) if data.get("ambient") else None
        self.rooms = [Room(r) for r in data.get("rooms", [])]
        self.doors = [pygame.Rect(d["rect"]) for d in data.get("doors", [])]
        painting = assets.optional(data.get("background", ""))
        self.props = [Prop(p, painted=painting is not None) for p in data.get("props", [])]
        self.by_id = {p.id: p for p in self.props if p.id}
        self.solids = [p.solid for p in self.props if p.solid]
        self.sprites = [p for p in self.props if p.image and not p.flat]
        self.lights = [p.light for p in self.props if p.light]
        self.ground = painting.convert() if painting else self._paint()
        self.low = pygame.Surface(VIEW.size).convert()
        self.dark = pygame.Surface(VIEW.size).convert()
        self.cam = pygame.Vector2()

    # ---------------------------------------------------------------- building

    def _paint(self):
        ground = pygame.Surface(self.size).convert()
        ground.fill((18, 16, 20))
        for room in self.rooms:
            r = paint.rng(self.name, *room.rect)
            rect = room.rect
            ground.set_clip(rect)
            paint.floor(ground, rect, room.data.get("floor", "planks"), r)
            if room.wall:
                paint.wall(ground, (rect.x, rect.y, rect.w, room.wall_h), room.wall, r)
                top = paint.wall_top(room.wall)
                for edge in ((rect.x, rect.y, rect.w, 2), (rect.x, rect.y, 2, rect.h), (rect.right - 2, rect.y, 2, rect.h),
                             (rect.x, rect.bottom - 2, rect.w, 2)):
                    ground.fill(top, edge)
            if room.data.get("roof"):
                doors = [d.x - rect.x for d in self.doors if d.colliderect((rect.x, rect.bottom - 3, rect.w, 6))]
                room.roof = paint.roof(rect.w, rect.h, room.data["roof"], doors, room.wall, r)
        for door in self.doors:
            ground.set_clip(door)
            paint.floor(ground, door, "threshold", paint.rng(self.name, *door))
        ground.set_clip(None)
        shadows = pygame.Surface(self.size, pygame.SRCALPHA)
        for prop in self.props:
            if prop.image and prop.flat:
                ground.blit(prop.image, prop.rect)
            elif prop.image and not prop.wall:
                pygame.draw.ellipse(shadows, (0, 0, 0, 70), (prop.rect.x - 1, prop.rect.bottom - 4, prop.rect.w + 2, 7))
        ground.blit(shadows, (0, 0))
        return ground

    # ---------------------------------------------------------------- rules

    def _open(self, x, y):
        """Whether one point of the floor can be stood on."""
        if any(d.collidepoint(x, y) for d in self.doors):
            return True
        for room in reversed(self.rooms):
            if room.rect.collidepoint(x, y):
                return room.floor.collidepoint(x, y)
        return False

    def walkable(self, feet):
        if feet.collidelist(self.solids) >= 0:
            return False
        return all(self._open(x, y) for x in (feet.left, feet.right - 1) for y in (feet.top, feet.bottom - 1))

    def nearest(self, feet, props):
        """The prop from the list that the feet are standing at, the closest if there are several."""
        best, best_d = None, None
        for prop in props:
            if prop.reach().colliderect(feet):
                box = prop.solid or prop.rect
                d = math.hypot(max(box.left - feet.centerx, 0, feet.centerx - box.right),
                               max(box.top - feet.centery, 0, feet.centery - box.bottom))
                if best is None or d < best_d:
                    best, best_d = prop, d
        return best

    def update(self, dt, pos):
        """Roofs lift off the house the ghost is in."""
        for room in self.rooms:
            if room.roof:
                goal = 0.0 if room.rect.collidepoint(pos) else 1.0
                room.cover += max(-dt * 5, min(dt * 5, goal - room.cover))

    # ---------------------------------------------------------------- drawing

    def look_at(self, pos):
        for axis, (size, view) in enumerate(zip(self.size, VIEW.size)):
            centre = round(pos[axis]) - view // 2 - (10 if axis else 0)
            self.cam[axis] = max(0, min(size - view, centre)) if size > view else (size - view) // 2

    def to_screen(self, pos):
        return (pos[0] - self.cam.x) * settings.PIXEL, (pos[1] - self.cam.y) * settings.PIXEL

    def draw(self, screen, actors, lights=(), outlines=()):
        """actors: (y of the feet, picture, top left) for everybody who walks about.
        lights: extra (x, y, radius, colour). outlines: (rect, colour) frames drawn unlit."""
        low, cx, cy = self.low, int(self.cam.x), int(self.cam.y)
        seen = VIEW.move(cx, cy)
        if cx < 0 or cy < 0:
            low.fill((18, 16, 20))
        low.blit(self.ground, (0, 0), seen) if cx >= 0 and cy >= 0 else low.blit(self.ground, (-cx, -cy))

        things = [(p.base, 0, p.image, p.rect.topleft) for p in self.sprites if p.rect.colliderect(seen)]
        for base, image, topleft in actors:
            low.blit(_shadow(image.get_width()), (topleft[0] - cx, round(base) - 3 - cy))
            things.append((base, 1, image, topleft))
        for room in self.rooms:
            if room.roof and room.cover > 0.02 and room.rect.colliderect(seen):
                room.roof.set_alpha(int(255 * room.cover))
                things.append((room.rect.bottom, 2, room.roof, room.rect.topleft))
        things.sort(key=lambda thing: thing[:2])
        for _, _, image, (x, y) in things:
            low.blit(image, (x - cx, y - cy))

        if self.ambient:
            self.dark.fill(self.ambient)
            for x, y, radius, color in list(self.lights) + list(lights):
                if seen.inflate(radius * 2, radius * 2).collidepoint(x, y):
                    self.dark.blit(_glow(radius, color), (x - radius - cx, y - radius - cy), special_flags=pygame.BLEND_RGB_ADD)
            low.blit(self.dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        for rect, color in outlines:
            pygame.draw.rect(low, color, pygame.Rect(rect).move(-cx, -cy).inflate(4, 4), 1)
        try:
            pygame.transform.scale(low, (settings.W, settings.H), screen)
        except ValueError:          # a screen with another pixel format
            screen.blit(pygame.transform.scale(low, (settings.W, settings.H)), (0, 0))


def _glow(radius, color):
    """A soft-edged disc of light in a few flat steps, like the rest of the pixel art."""
    key = (radius, color)
    if key not in _glows:
        img = pygame.Surface((radius * 2, radius * 2))
        steps = 6
        for i in range(steps):
            pygame.draw.circle(img, [c * (i + 1) // steps for c in color], (radius, radius), radius * (steps - i) // steps)
        _glows[key] = img.convert()
    return _glows[key]


def _shadow(width):
    if width not in _shadows:
        img = pygame.Surface((width, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(img, (0, 0, 0, 80), (1, 0, width - 2, 5))
        _shadows[width] = img
    return _shadows[width]
