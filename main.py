import asyncio

import pygame

from game.app import Game
from game.display import Display


async def main():
    pygame.init()
    display = Display()
    game = Game(display)

    while game.running:
        game.update(display.tick(), pygame.event.get())
        game.draw()
        display.present()
        await asyncio.sleep(0)      # hands the frame to the browser; the web build needs it

    pygame.quit()


asyncio.run(main())
