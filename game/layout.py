"""The museum floor plan, in world pixels. Plain data: the game and the
placeholder painter both read it, so moving a room here moves it everywhere.

A painted map replaces assets/img/map.png; keep rooms and doors where they
are here (or change both together).
"""

WORLD = (3400, 1900)

# name: (x, y, w, h) of the floor
ROOMS = {
    "fuajee": (1200, 900, 1000, 700),
    "linn": (150, 750, 900, 1000),
    "vald": (2350, 750, 900, 1000),
    "hoim": (1150, 100, 1100, 650),
}

WINGS = {
    "linn": {"name": "Linnasaal", "sub": "Tartu majad, 1887", "unlock": 0,
             "door": (1050, 1180, 150, 140), "accent": (92, 122, 160)},
    "vald": {"name": "Vallasaal", "sub": "vallakohtute protokollid", "unlock": 2,
             "door": (2200, 1180, 150, 140), "accent": (170, 84, 60)},
    "hoim": {"name": "Hõimusaal", "sub": "sugulasrahvaste asjad", "unlock": 5,
             "door": (1630, 750, 140, 150), "accent": (150, 60, 70)},
}

START = (1700, 1330)
BOARD = (1400, 960)           # Liis's notes, on the lobby's top wall
ENTRANCE = (1700, 1560)       # the front door, bottom of the lobby
OPEN_AT = 6                   # records needed before the door can be opened

# four exhibit plinths per wing, along the top wall
PLINTHS = {
    "linn": [(290, 880), (490, 880), (710, 880), (910, 880)],
    "vald": [(2490, 880), (2690, 880), (2910, 880), (3110, 880)],
    "hoim": [(1330, 230), (1560, 230), (1840, 230), (2070, 230)],
}

# (kind, x, y, w, h): furniture, drawn top-down. The ghost floats over all of it.
PROPS = {
    "fuajee": [
        ("rug_round", 1700, 1260, 520, 380), ("sofa", 1330, 1420, 190, 80), ("sofa", 2070, 1420, 190, 80),
        ("plant", 1250, 960, 0, 0), ("plant", 2150, 960, 0, 0), ("plant", 1250, 1540, 0, 0), ("plant", 2150, 1540, 0, 0),
        ("desk", 1960, 1010, 260, 90), ("lamp", 1820, 1000, 0, 0), ("lamp", 1560, 1000, 0, 0),
        ("cart", 1480, 1130, 110, 70),
    ],
    "linn": [
        ("rug", 600, 1300, 560, 300), ("table", 360, 1140, 220, 120), ("table", 820, 1140, 220, 120),
        ("table", 600, 1300, 260, 130), ("shelf", 250, 1500, 60, 300), ("shelf", 950, 1500, 60, 300),
        ("plant", 210, 1090, 0, 0), ("plant", 990, 1090, 0, 0), ("lamp", 600, 1090, 0, 0),
        ("cabinet", 420, 1650, 200, 70), ("cabinet", 780, 1650, 200, 70), ("lamp", 600, 1560, 0, 0),
        ("chair", 360, 1250, 0, 0), ("chair", 820, 1250, 0, 0),
    ],
    "vald": [
        ("rug", 2800, 1320, 600, 320), ("table", 2800, 1200, 420, 110), ("bench", 2620, 1420, 240, 50),
        ("bench", 2980, 1420, 240, 50), ("bench", 2620, 1520, 240, 50), ("bench", 2980, 1520, 240, 50),
        ("stove", 2450, 1090, 110, 110), ("shelf", 3150, 1300, 60, 280), ("plant", 3180, 1090, 0, 0),
        ("lamp", 2800, 1080, 0, 0), ("cabinet", 2560, 1660, 200, 70), ("cabinet", 3040, 1660, 200, 70),
        ("chair", 2700, 1120, 0, 0), ("chair", 2800, 1120, 0, 0), ("chair", 2900, 1120, 0, 0), ("lamp", 2800, 1640, 0, 0),
    ],
    "hoim": [
        ("rug_woven", 1700, 500, 640, 240), ("shelf_low", 1300, 440, 200, 60), ("shelf_low", 2100, 440, 200, 60),
        ("loom", 1440, 610, 170, 110), ("crate", 1260, 640, 80, 80), ("crate", 2140, 640, 80, 80),
        ("plant", 1210, 330, 0, 0), ("plant", 2190, 330, 0, 0), ("lamp", 1700, 380, 0, 0),
        ("table", 1960, 610, 200, 100), ("lamp", 1260, 540, 0, 0), ("lamp", 2140, 540, 0, 0),
    ],
}

# where memory fragments rest: three per record, twelve per wing
SPOTS = {
    "linn": [(360, 1060), (820, 1060), (600, 1210), (300, 1320), (900, 1320), (250, 1690), (950, 1690),
             (600, 1470), (420, 1580), (780, 1580), (210, 1180), (990, 1200)],
    "vald": [(2450, 1200), (2800, 1290), (2620, 1370), (2980, 1370), (2500, 1520), (3100, 1520), (3150, 1120),
             (2560, 1590), (3040, 1590), (2800, 1480), (2420, 1690), (3190, 1690)],
    "hoim": [(1300, 380), (2100, 380), (1440, 520), (1960, 520), (1260, 560), (2140, 560), (1700, 400),
             (1700, 620), (1560, 690), (1840, 690), (1220, 700), (2180, 700)],
}
