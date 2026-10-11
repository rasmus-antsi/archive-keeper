"""Turns the artists' pictures in art-src/ into the files the game loads.

    venv/bin/python tools/import_art.py

Each picture is cut down to what is drawn on it (the artists leave a margin), and one
that was saved on a white background gets a see-through one. The table says where
each picture goes; add a line when a new one arrives in the Drive.

A picture that was saved enlarged, every drawn pixel many pixels wide, is listed as
(file, how many drawn pixels wide it really is) and brought back to that size.
"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

SOURCE, TARGET = "art-src", "assets/img"

ART = {
    # things found in a memory, shown large in chests and on the document
    "Objektid/Küünal.png": "objektid/kyynal.png",
    "Objektid/Pudel.png": "objektid/pudel.png",
    "Objektid/Raamat.png": "objektid/raamat.png",
    "Objektid/Taskukell.png": "objektid/taskukell.png",
    "Objektid/Tint.png": "objektid/tint.png",
    "Objektid/Võti.png": "objektid/voti.png",
    "Objektid/Vale_Objekt1.png": "objektid/sekstant.png",
    "Objektid/Trükimasin.png": "objektid/trykimasin.png",
    ("Objektid/pileofmail.png", 43): "objektid/kirjad.png",
    # the town hall square in winter; a prop's picture is named after its type (see game/world.py)
    "Objektid/Kaev.png": "props/well.png",
    "Objektid/Kuusk.png": "props/spruce.png",
    "Objektid/Lamp.png": "props/streetlamp.png",
    "Objektid/Lumi1.png": "props/snow.png",
    "Objektid/Lumi2.png": "props/snow-2.png",
    "Objektid/Lumi3.png": "props/snow-3.png",
    "Objektid/Majad.png": "props/houses.png",
    "Objektid/Poodu.png": "props/gallows.png",
    "Objektid/Purskaev.png": "props/fountain.png",
    "Objektid/Raemaja.png": "props/townhall.png",
    # the archive's furniture; "-open" is the same piece with a door ajar
    "Raamatukogu/diivan.png": "props/sofa.png",
    "Raamatukogu/tugitool.png": "props/armchair.png",
    "Raamatukogu/laud.png": "props/table.png",
    "Raamatukogu/väike laud.png": "props/sidetable.png",
    "Raamatukogu/vaip.png": "props/rug.png",
    "Raamatukogu/lamp sees.png": "props/lamp.png",        # lamp.png has a faint black sheet behind it
    "Raamatukogu/kell.png": "props/clock.png",
    "Raamatukogu/suur kapp kinni.png": "props/bookcase.png",
    "Raamatukogu/suur kapp lahti.png": "props/bookcase-open.png",
    "Raamatukogu/suur kapp2 kinni.png": "props/bookcase-2.png",
    "Raamatukogu/suur kapp2 lahti.png": "props/bookcase-2-open.png",
    "Raamatukogu/väike kapp kinni.png": "props/cupboard.png",
    "Raamatukogu/väike kapp lahti.png": "props/cupboard-open.png",
    "Raamatukogu/kapp suur külg.png": "props/bookcase-side.png",
    "Raamatukogu/kapp väike külg.png": "props/cupboard-side.png",
}


def cut_white(img):
    """Patches of the white background become see-through, also the ones the drawing
    closes in (the gaps in the sextant's frame). A few white pixels of highlight stay."""
    white = pygame.mask.from_threshold(img, (255, 255, 255), (8, 8, 8, 255))
    for patch in white.connected_components(12):
        patch.to_surface(img, setcolor=(0, 0, 0, 0), unsetcolor=None)


def shrink(img, across):
    """An enlarged picture at its drawn size: one pixel from the middle of each block."""
    block = img.get_width() / across
    small = pygame.Surface((across, round(img.get_height() / block)), pygame.SRCALPHA)
    for y in range(small.get_height()):
        for x in range(across):
            small.set_at((x, y), img.get_at((int((x + 0.5) * block), int((y + 0.5) * block))))
    return small


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    for source, target in ART.items():
        source, across = source if isinstance(source, tuple) else (source, None)
        loaded = pygame.image.load(f"{SOURCE}/{source}")
        img = loaded.convert_alpha()
        if across:
            img = shrink(img, across)
        if not loaded.get_flags() & pygame.SRCALPHA:
            cut_white(img)
        img = img.subsurface(img.get_bounding_rect()).copy()
        os.makedirs(os.path.dirname(f"{TARGET}/{target}"), exist_ok=True)
        pygame.image.save(img, f"{TARGET}/{target}")
        print(f"{target:32s} {img.get_width()}x{img.get_height()}")


main()
