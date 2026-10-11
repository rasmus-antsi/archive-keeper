"""Sizes, colours and font roles. Change a look here and it changes everywhere."""

TITLE = "Archive Keeper"

# Everything is laid out for a Full HD screen: art, positions in data/ and text
# sizes are all in 1920x1080 pixels. The window may be any size; game/display.py
# fits the picture into it.
W, H = 1920, 1080
FPS = 60

# How much sound the mixer hands over at a time, in samples (2048 is 46 ms). In the
# browser sound is mixed between frames, so a frame that takes longer than this is
# heard as a pop; pygame's own 512 (12 ms) popped whenever a menu opened.
AUDIO_BUFFER = 2048

# The rooms the ghost walks in are pixel art: one art pixel is PIXEL screen pixels,
# so the screen shows VIEW_W x VIEW_H of them at a time (see game/world.py).
# Interface pictures (portraits, documents) taller than SPRITE_BIG are used as they are.
PIXEL = 8
VIEW_W, VIEW_H = W // PIXEL, H // PIXEL
SPRITE_BIG = 100

CREAM = (240, 232, 212)
INK = (38, 30, 28)
PAPER = (232, 220, 194)
TEAL = (130, 226, 214)
WARM = (255, 206, 130)
DIM = (150, 150, 160)
RED = (214, 96, 84)
NIGHT = (16, 16, 22)

# role -> font file in assets/fonts
FONTS = {
    "title": "UnifrakturMaguntia-Book.ttf",   # headings, places, document titles
    "pixel": "Jersey10-Regular.ttf",          # everything else on the screen: menus, hints, everything said
    "body": "CrimsonText-Regular.ttf",        # these three only on paper, the record page of an open shelf
    "italic": "CrimsonText-Italic.ttf",
    "bold": "CrimsonText-SemiBold.ttf",
}
