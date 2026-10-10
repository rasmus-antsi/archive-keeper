"""Cached loading of images, fonts, sounds and music.

Missing art never crashes the game: sprite() returns a pink box, and backdrop()
and optional() return None so a scene can draw its own stand-in.
"""
import os

import pygame

from . import settings

_fonts, _images, _sprites, _backdrops, _photos, _sounds = {}, {}, {}, {}, {}, {}
_music = None
muted = False


def font(role, size):
    key = (role, size)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(f"assets/fonts/{settings.FONTS[role]}", size)
    return _fonts[key]


def optional(name):
    """An image exactly as it was saved, or None if the file is not there yet."""
    if name not in _images:
        path = f"assets/img/{name}"
        try:
            _images[name] = pygame.image.load(path).convert_alpha() if name and os.path.isfile(path) else None
        except pygame.error:
            _images[name] = None
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
        _sprites[key] = enlarge(img, k)
    return _sprites[key]


def enlarge(img, k):
    return img if k == 1 else pygame.transform.scale_by(img, k)


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
    """A photograph smooth-scaled to fit inside box (w, h)."""
    key = (name, box)
    if key not in _photos:
        img = optional(name)
        if img is not None:
            k = min(box[0] / img.get_width(), box[1] / img.get_height())
            img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
        if len(_photos) > 40:
            _photos.clear()
        _photos[key] = img
    return _photos[key]


def play(name, volume=1.0):
    if name not in _sounds:
        path = f"assets/snd/{name}"
        try:
            _sounds[name] = pygame.mixer.Sound(path) if os.path.isfile(path) else None
        except pygame.error:
            _sounds[name] = None
    snd = _sounds[name]
    if snd:
        snd.set_volume(volume)
        snd.play()


def music(name, volume=0.5):
    """Loop assets/music/<name>.ogg. Silently does nothing until the file exists."""
    global _music
    if name == _music:
        return
    _music = name
    try:
        pygame.mixer.music.fadeout(400)
        path = f"assets/music/{name}.ogg"
        if name and os.path.isfile(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0 if muted else volume)
            pygame.mixer.music.play(-1, fade_ms=800)
    except pygame.error:
        pass


def toggle_mute():
    global muted
    muted = not muted
    try:
        pygame.mixer.music.set_volume(0 if muted else 0.5)
    except pygame.error:
        pass
