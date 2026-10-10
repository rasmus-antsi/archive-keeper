"""Makes favicon.png from the ghost's sprite: its head on a dark tile.

pygbag uses a favicon.png next to main.py as the browser tab's icon, and
game/display.py uses the same file as the window's icon on the desktop.

    venv/bin/python tools/make_icon.py
"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()
pygame.display.set_mode((1, 1))
ghost = pygame.image.load("assets/img/tegelased/down.png").convert_alpha()
head = ghost.subsurface((0, 1, 14, 14))                    # the head and the shoulders
icon = pygame.Surface((64, 64), pygame.SRCALPHA)
pygame.draw.rect(icon, (22, 20, 26), icon.get_rect(), border_radius=12)
icon.blit(pygame.transform.scale_by(head, 4), (4, 6))
pygame.image.save(icon, "favicon.png")
print("wrote favicon.png")
