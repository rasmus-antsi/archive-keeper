import asyncio

import pygame

from game import core
from game.app import Game


async def main():
    pygame.init()
    screen = pygame.display.set_mode((core.W, core.H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Arhiivihoidja")
    clock = pygame.time.Clock()
    game = Game(screen)

    while game.running:
        dt = min(clock.tick(core.FPS) / 1000, 0.05)
        game.update(dt, pygame.event.get())
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)  # required for the browser build

    pygame.quit()


asyncio.run(main())
