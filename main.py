import asyncio

import pygame

from game import settings
from game.app import Game
from game.display import Display


async def main():
    pygame.init()
    display = Display()
    clock = pygame.time.Clock()
    game = Game(display)

    while game.running:
        dt = min(clock.tick(settings.FPS) / 1000, 0.05)
        game.update(dt, pygame.event.get(), clock.get_fps())
        game.draw()
        display.present()
        await asyncio.sleep(0)  # required for the browser build

    pygame.quit()


asyncio.run(main())
