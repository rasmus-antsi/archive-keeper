"""A place the ghost walks around in, larger than the screen: rooms, doorways, furniture,
roofs, lamplight and the camera that follows the ghost.

Everything here is measured in art pixels, the pixels the artists draw. The world is
drawn small (settings.VIEW, 240x135) and enlarged settings.PIXEL times onto the
screen in one step, which keeps it crisp and fast in the browser.

The camera is not held to whole art pixels: the enlarged picture is shifted by the
part of a pixel that is left over, so the view scrolls one screen pixel at a time
instead of eight. The ghost is drawn afterwards at its exact place for the same reason.

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

PIXEL = settings.PIXEL
VIEW = pygame.Rect(0, 0, settings.VIEW_W, settings.VIEW_H)
REACH = 9                      # how close to a thing counts as standing at it
FOLLOW = 9.0                   # how eagerly the camera catches up with the ghost; bigger is tighter
JUMP = 40                      # further than this from where it belongs, the camera jumps instead of gliding
VOID = (18, 16, 20)            # what lies outside every room
_glows, _shadows, _canvases = {}, {}, []


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
        if self.type not in paint.PROPS:
            raise ValueError(f"a map has a prop of type '{self.type}'; the types are: {', '.join(sorted(paint.PROPS))}")
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
        self.cam = pygame.Vector2()       # top left corner of the view, exact
        self.origin = (0, 0)              # the same in whole screen pixels

    # ---------------------------------------------------------------- building

    def _paint(self):
        ground = pygame.Surface(self.size).convert()
        ground.fill(VOID)
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

    # ---------------------------------------------------------------- camera

    def look_at(self, pos, dt=0.0):
        """Bring the camera towards pos, the ghost's feet. It glides there over a few
        frames; with no dt, or when it has far to go, it is put there at once."""
        for axis, (size, view) in enumerate(zip(self.size, VIEW.size)):
            goal = pos[axis] - view / 2 - (10 if axis else 0)
            goal = max(0, min(size - view, goal)) if size > view else (size - view) / 2
            gap = goal - self.cam[axis]
            self.cam[axis] = goal if not dt or abs(gap) > JUMP else goal - gap * math.exp(-FOLLOW * dt)
        self.origin = (round(self.cam.x * PIXEL), round(self.cam.y * PIXEL))

    def to_screen(self, pos):
        return pos[0] * PIXEL - self.origin[0], pos[1] * PIXEL - self.origin[1]

    # ---------------------------------------------------------------- drawing

    def draw(self, screen, ghost=None, actors=(), lights=(), outlines=()):
        """ghost: the Player, drawn sharp and last, at its exact place.
        actors: (y of the feet, picture, top left) for everybody else who walks about.
        lights: extra (x, y, radius, colour). outlines: (rect, colour) frames drawn unlit."""
        low, dark, big = _canvas()
        ox, oy = self.origin
        cx, cy = ox // PIXEL, oy // PIXEL             # the art pixel in the top left corner
        seen = pygame.Rect((cx, cy), low.get_size())
        low.fill(VOID)
        low.blit(self.ground, (-cx, -cy))

        # (y it is sorted by, layer, picture, top left, see-through or None)
        things = [(p.base, 0, p.image, p.rect.topleft, None) for p in self.sprites if p.rect.colliderect(seen)]
        for base, image, topleft in actors:
            low.blit(_shadow(image.get_width()), (topleft[0] - cx, round(base) - 3 - cy))
            things.append((base, 1, image, topleft, None))
        for room in self.rooms:
            if room.roof and room.cover > 0.02 and room.rect.colliderect(seen):
                things.append((room.rect.bottom, 2, room.roof, room.rect.topleft, int(255 * room.cover)))
        things.sort(key=lambda thing: thing[:2])
        for _, _, image, (x, y), alpha in things:
            if alpha is not None:
                image.set_alpha(alpha)
            low.blit(image, (x - cx, y - cy))

        if self.ambient:
            dark.fill(self.ambient)
            for x, y, radius, color in list(self.lights) + list(lights):
                if seen.inflate(radius * 2, radius * 2).collidepoint(x, y):
                    dark.blit(_glow(radius, color), (x - radius - cx, y - radius - cy), special_flags=pygame.BLEND_RGB_ADD)
            low.blit(dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        for rect, color in outlines:
            pygame.draw.rect(low, color, pygame.Rect(rect).move(-cx, -cy).inflate(4, 4), 1)

        # enlarge, and slide the picture back by the part of an art pixel the camera has moved
        pygame.transform.scale(low, big.get_size(), big)
        screen.blit(big, (cx * PIXEL - ox, cy * PIXEL - oy))
        if ghost:
            self._draw_ghost(screen, ghost, things, low, seen)

    def _draw_ghost(self, screen, ghost, things, low, seen):
        """The ghost goes straight onto the screen, placed to the screen pixel, so it glides
        instead of hopping from one art pixel to the next. It is not lit: it glows by itself.
        Whatever stands in front of it is then cut out of the finished small picture and
        drawn over it again."""
        ox, oy = self.origin
        w, h = ghost.image.get_size()
        picture = ghost.picture
        left = round(ghost.pos.x * PIXEL) - picture.get_width() // 2 - ox
        foot = round((ghost.pos.y - 1 + ghost.lift) * PIXEL) - oy
        screen.blit(_shadow(w, big=True), (left, round((ghost.pos.y - 3) * PIXEL) - oy))
        screen.blit(picture, (left, foot - picture.get_height()))

        box = pygame.Rect(math.floor(ghost.pos.x - w / 2), math.floor(ghost.pos.y - h - 2), w + 2, h + 5)
        for base, layer, image, (x, y), alpha in things:
            if (base, layer) <= (ghost.pos.y, 1):
                continue                                # behind the ghost
            part = box.clip(pygame.Rect((x, y), image.get_size())).clip(seen)
            if not part.w or not part.h:
                continue
            piece = low.subsurface(part.move(-seen.x, -seen.y))
            if alpha is None:
                # a prop or a person: only where its own picture is solid, in the lit colours it has on screen
                cut = pygame.Surface(part.size, pygame.SRCALPHA)
                cut.blit(image, (0, 0), part.move(-x, -y))
                cut.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
                cut.blit(piece, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                piece = cut
            piece = pygame.transform.scale_by(piece, PIXEL)
            if alpha is not None:
                piece.set_alpha(alpha)                  # a roof that is fading away
            screen.blit(piece, (part.x * PIXEL - ox, part.y * PIXEL - oy))


def _canvas():
    """The small picture the world is drawn on, its darkness layer, and the enlarged copy.
    One art pixel wider and taller than the view, to have something to scroll into."""
    if not _canvases:
        size = (VIEW.w + 1, VIEW.h + 1)
        _canvases.extend((pygame.Surface(size).convert(), pygame.Surface(size).convert(),
                          pygame.Surface((size[0] * PIXEL, size[1] * PIXEL)).convert()))
    return _canvases


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


def _shadow(width, big=False):
    """The soft patch under somebody's feet; big is the same picture at screen size."""
    key = (width, big)
    if key not in _shadows:
        img = pygame.Surface((width, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(img, (0, 0, 0, 80), (1, 0, width - 2, 5))
        _shadows[key] = pygame.transform.scale_by(img, PIXEL) if big else img
    return _shadows[key]
