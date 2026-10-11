"""Cached loading of images, fonts, sounds and music.

Missing art never crashes the game: sprite() returns a pink box, and backdrop()
and optional() return None so a scene can draw its own stand-in.
"""
import collections
import os

import pygame

from . import settings

_fonts, _images, _sprites, _backdrops, _sounds = {}, {}, {}, {}, {}
_photos = collections.OrderedDict()        # scaled photographs, the most recently shown last
PHOTOS_KEPT = 24
KEY = (255, 0, 255)                        # the colour that stands for "see-through" in hardened pictures

levels = {"music": 1.0, "sound": 1.0}      # what the player chose in the settings, 0..1
muted = False
track_levels = {}                          # track name -> how loud that file should play, from data/game.json
TRACK_LEVEL = 0.5
FADE_OUT, FADE_IN = 0.35, 0.9              # seconds to fade the old track out and the new one in
HUSH = 0.45                                # how loud the music stays while the game is paused

_wanted = _playing = None                  # the track that was asked for, and the one that is loaded
_fade = 0.0                                # how far the loaded track has faded in, 0..1
_hushed, _hush = False, 0.0                # whether the music should be held down, and how far it is, 0..1
_heard = None                              # the volume the mixer was last given


# ---------------------------------------------------------------- pictures and fonts

def font(role, size):
    key = (role, size)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(f"assets/fonts/{settings.FONTS[role]}", size)
    return _fonts[key]


def _load(name):
    path = f"assets/img/{name}"
    if not name or not os.path.isfile(path):
        return None
    try:
        img = pygame.image.load(path)
    except pygame.error:
        return None
    # a picture with no see-through parts (a photograph) is several times faster to draw this way
    see_through = img.get_flags() & pygame.SRCALPHA or img.get_colorkey() is not None
    return img.convert_alpha() if see_through else img.convert()


def optional(name):
    """An image exactly as it was saved, or None if the file is not there yet."""
    if name not in _images:
        _images[name] = _load(name)
    return _images[name]


def sprite(name, scale=None, missing=(14, 25)):
    """A character or prop, ready to draw on the 1920x1080 screen.

    Small pixel art is enlarged settings.PIXEL times with hard edges; art already
    drawn at full size is left alone. Pass scale to choose the enlargement yourself.
    A missing file becomes a pink box so the game still runs.
    """
    key = (name, scale)
    if key not in _sprites:
        img = optional(name)
        if img is None:
            img = pygame.Surface(missing, pygame.SRCALPHA)
            img.fill((200, 60, 120, 200))
            pygame.draw.rect(img, (255, 255, 255), img.get_rect(), 1)
        k = scale or (settings.PIXEL if img.get_height() < settings.SPRITE_BIG else 1)
        _sprites[key] = harden(enlarge(img, k))
    return _sprites[key]


def enlarge(img, k):
    return img if k == 1 else pygame.transform.scale_by(img, k)


def harden(img):
    """Pixel art has no half-see-through pixels, and such a picture draws far faster when
    "see-through" is one reserved colour instead of a value kept in every pixel: in the
    browser the big portrait went from 3.8 ms to 0.04 ms.

    A few stray faint pixels, left over from cutting a white background away, are dropped.
    A picture with really soft edges is left as it is.
    """
    if not img.get_flags() & pygame.SRCALPHA:
        return img
    pixels = img.get_width() * img.get_height()
    soft = pygame.mask.from_surface(img, 24).count() - pygame.mask.from_surface(img, 230).count()
    if soft > pixels * 0.005:
        return img
    shape = pygame.mask.from_surface(img, 127)
    flat = pygame.Surface(img.get_size()).convert()
    flat.fill(KEY)
    # copied, not drawn: drawn, a pixel that is a little see-through takes on some of the reserved colour
    shape.to_surface(flat, setsurface=img.convert(), unsetcolor=None)
    if pygame.mask.from_threshold(flat, KEY, (1, 1, 1, 255)).count() != pixels - shape.count():
        return img                                  # the picture uses the reserved colour itself
    flat.set_colorkey(KEY, pygame.RLEACCEL)
    return flat


def backdrop(name):
    """A full-screen background stretched to 1920x1080, or None if the file is missing.
    Pixel art (an exact fraction of the screen, like 320x180) keeps its hard edges."""
    if name not in _backdrops:
        img = optional(name)
        if img is not None and img.get_size() != (settings.W, settings.H):
            exact = settings.W % img.get_width() == 0 and settings.H % img.get_height() == 0
            resize = pygame.transform.scale if exact else pygame.transform.smoothscale
            img = resize(img, (settings.W, settings.H))
        _backdrops[name] = img.convert() if img is not None else None
    return _backdrops[name]


def photo(name, box):
    """A photograph smooth-scaled to fit inside box (w, h), or None if the file is missing.

    The archive holds 150 of them, so the file as it was saved is not kept, and only
    the scaled copies of the last few shown are.
    """
    key = (name, box)
    if key in _photos:
        _photos.move_to_end(key)
        return _photos[key]
    img = _load(name)
    if img is not None:
        k = min(box[0] / img.get_width(), box[1] / img.get_height())
        img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
    _photos[key] = img
    if len(_photos) > PHOTOS_KEPT:
        _photos.popitem(last=False)
    return img


def photo_ready(name, box):
    """Whether photo() would answer at once, without reading a file."""
    return (name, box) in _photos


# ---------------------------------------------------------------- sounds

def sound(name):
    """Load a sound without playing it, so its first use does not stutter."""
    if name not in _sounds:
        path = f"assets/snd/{name}"
        try:
            _sounds[name] = pygame.mixer.Sound(path) if os.path.isfile(path) else None
        except pygame.error:
            _sounds[name] = None
    return _sounds[name]


def play(name, volume=1.0):
    snd = sound(name)
    if snd and not muted and levels["sound"] > 0:
        snd.set_volume(volume * levels["sound"])
        snd.play()


def toggle_mute():
    global muted
    muted = not muted
    return muted


# ---------------------------------------------------------------- music

def music(name):
    """Ask for assets/music/<name>.ogg to loop. update() makes the change, gradually.
    Nothing plays until the file exists."""
    global _wanted
    _wanted = name


def hush(on):
    """Hold the music down (behind the pause menu) or let it up again."""
    global _hushed
    _hushed = on


def update(dt):
    """Once a frame: fade the old track out, start the one that was asked for, fade it in.

    The fades are done here, a step at a time, because pygame's own fadeout() stops
    the whole game in the browser until the fade is over.
    """
    global _playing, _fade, _hush
    if _wanted != _playing:
        _fade -= dt / FADE_OUT
        if _fade <= 0:
            _playing, _fade = _wanted, 0.0
            _start(_playing)
    elif _fade < 1:
        _fade = min(1.0, _fade + dt / FADE_IN)
    _hush = max(0.0, min(1.0, _hush + (dt if _hushed else -dt) / 0.25))
    level = _fade * (1 - (1 - HUSH) * _hush) * levels["music"] * track_levels.get(_playing, TRACK_LEVEL)
    _listen(0.0 if muted else level)


def _start(name):
    global _heard
    try:
        pygame.mixer.music.stop()
        path = f"assets/music/{name}.ogg"
        if name and os.path.isfile(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0)
            pygame.mixer.music.play(-1)
            _heard = 0.0
    except pygame.error:
        pass


def _listen(volume):
    """Give the mixer a new music volume, but only when it has really changed."""
    global _heard
    if _heard is None or abs(volume - _heard) > 0.004 or (volume == 0) != (_heard == 0):
        _heard = volume
        try:
            pygame.mixer.music.set_volume(volume)
        except pygame.error:
            pass
