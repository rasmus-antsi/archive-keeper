"""Sizes, colours and font roles. Change a look here and it changes everywhere."""

TITLE = "Archive Keeper"

# The world is pixel art drawn on a small canvas and scaled up with hard pixels.
# Text and photos are drawn afterwards at full window resolution so they stay sharp.
CANVAS_W, CANVAS_H = 320, 240
SCALE = 3
W, H = CANVAS_W * SCALE, CANVAS_H * SCALE
FPS = 60

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
    "body": "CrimsonText-Regular.ttf",        # dialogue and long text
    "italic": "CrimsonText-Italic.ttf",
    "bold": "CrimsonText-SemiBold.ttf",
    "mono": "CourierPrime-Regular.ttf",       # the robots and all interface hints
}
