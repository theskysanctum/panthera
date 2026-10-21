#!/usr/bin/env python3
"""Resume/Quit window shown when the pause hotkey is pressed (see pause_supervisor.py). Launched
as its own short-lived process while the real game's whole process tree sits SIGSTOPped - see
pause_supervisor.py's own module docstring for the one open question about a second process
sharing the display with a merely-frozen (not exited) one.

Quit asks first - SIGKILLing the whole paused process tree with no way back is the one
destructive, unrecoverable action here. Resume doesn't need to ask - there's nothing to lose by
resuming.

Writes its result ("resume" or "quit") to the given file path and exits."""
import sys

import pygame

BG = (20, 20, 24)
FG = (235, 235, 235)
DIM = (140, 140, 150)
SEL_BG = (60, 90, 170)


def main():
    result_path = sys.argv[1]
    # pids (sys.argv[2]) aren't used by this minimal overlay - kept in the argv shape anyway so a
    # future per-emulator pause action (e.g. a save-state key injected via uinput) has them
    # without changing how pause_supervisor.py invokes this.

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    font = pygame.font.Font(None, 40)
    hint_font = pygame.font.Font(None, 24)

    options = ["Resume", "Quit"]
    selected = 0
    confirming_quit = False
    clock = pygame.time.Clock()
    result = "resume"

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if confirming_quit:
                    if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                        selected = 1 - selected
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if options[selected] == "Yes":
                            result = "quit"
                            running = False
                        else:
                            confirming_quit = False
                            options = ["Resume", "Quit"]
                            selected = 0
                    elif event.key == pygame.K_ESCAPE:
                        confirming_quit = False
                        options = ["Resume", "Quit"]
                        selected = 0
                else:
                    if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                        selected = 1 - selected
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if options[selected] == "Resume":
                            result = "resume"
                            running = False
                        else:
                            confirming_quit = True
                            options = ["Yes", "No"]
                            selected = 1  # "No" is always the default
                    elif event.key == pygame.K_ESCAPE:
                        result = "resume"
                        running = False

        screen.fill(BG)
        heading = "Quit?" if confirming_quit else "Paused"
        screen.blit(font.render(heading, True, FG), (screen.get_width() // 2 - 80, 160))
        if confirming_quit:
            msg = "This closes what's running right now. Any unsaved progress is lost."
            screen.blit(hint_font.render(msg, True, DIM), (screen.get_width() // 2 - 260, 220))
        for i, label in enumerate(options):
            color = SEL_BG if i == selected else BG
            x = screen.get_width() // 2 - 160 + i * 180
            rect = pygame.Rect(x, 280, 150, 60)
            pygame.draw.rect(screen, color, rect)
            screen.blit(font.render(label, True, FG), (rect.x + 20, rect.y + 12))
        screen.blit(hint_font.render("Left/Right: choose   Enter: select   Escape: back", True, DIM), (screen.get_width() // 2 - 220, 380))
        pygame.display.flip()
        clock.tick(30)

    with open(result_path, "w") as f:
        f.write(result)


if __name__ == "__main__":
    main()
