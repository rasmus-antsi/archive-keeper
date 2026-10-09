import asyncio
import pygame

W, H = 1920, 1080
SPEED = 300  # pixels per second


async def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Archive Keeper")
    clock = pygame.time.Clock()

    pos = pygame.Vector2(W / 2, H / 2)
    size = 40

    running = True
    while running:
        dt = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        if move.length() > 0:
            move = move.normalize()  # same speed on diagonals
        pos += move * SPEED * dt

        pos.x = max(0, min(W - size, pos.x))
        pos.y = max(0, min(H - size, pos.y))

        screen.fill((30, 32, 44))
        pygame.draw.rect(screen, (90, 200, 120), (pos.x, pos.y, size, size))
        pygame.display.flip()

        await asyncio.sleep(0)  # required for the browser build

    pygame.quit()


asyncio.run(main())
