"""Sizes, colours and font roles. Change a look here and it changes everywhere."""

TITLE = "Archive Keeper"

# Everything is laid out for a Full HD screen: art, positions in data/ and text
# sizes are all in 1920x1080 pixels. The window may be any size; game/display.py
# fits the picture into it.
W, H = 1920, 1080
FPS = 60

# Small pixel-art sprites are enlarged by a whole number so they stay crisp.
# A sprite drawn at full size (taller than SPRITE_BIG) is used as it is.
PIXEL = 6
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
    "body": "CrimsonText-Regular.ttf",        # dialogue and long text
    "italic": "CrimsonText-Italic.ttf",
    "bold": "CrimsonText-SemiBold.ttf",
    "mono": "CourierPrime-Regular.ttf",       # the robots and all interface hints
}
