#!/usr/bin/env python3
"""Resume/Music/Quit window shown when the pause hotkey is pressed (see pause_supervisor.py).
Launched as its own short-lived process while the real game's whole process tree sits SIGSTOPped -
see pause_supervisor.py's own module docstring for the one open question about a second process
sharing the display with a merely-frozen (not exited) one.

Quit asks first - SIGKILLing the whole paused process tree with no way back is the one
destructive, unrecoverable action here. Resume doesn't need to ask - there's nothing to lose by
resuming. Music opens a sub-view that controls the background Limusic player (see
limusic_control.py) rather than resuming or quitting anything.

Writes its result ("resume" or "quit") to the given file path and exits."""
import sys

import pygame

import limusic_control

BG = (20, 20, 24)
FG = (235, 235, 235)
DIM = (140, 140, 150)
SEL_BG = (60, 90, 170)

MUSIC_POLL_MS = 1000
ART_SIZE = 160


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

    view = "main"  # "main" | "quit_confirm" | "music"
    options = ["Resume", "Music", "Quit"]
    selected = 0
    clock = pygame.time.Clock()
    result = "resume"

    music_options = ["Previous", "Play/Pause", "Next", "Back"]
    music_selected = 1  # start on Play/Pause
    music_meta = None
    music_art_surface = None
    music_art_url = None
    last_poll = -MUSIC_POLL_MS

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if view == "quit_confirm":
                    if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                        selected = 1 - selected
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if options[selected] == "Yes":
                            result = "quit"
                            running = False
                        else:
                            view = "main"
                            options = ["Resume", "Music", "Quit"]
                            selected = 0
                    elif event.key == pygame.K_ESCAPE:
                        view = "main"
                        options = ["Resume", "Music", "Quit"]
                        selected = 0
                elif view == "music":
                    if event.key in (pygame.K_LEFT, pygame.K_UP):
                        music_selected = (music_selected - 1) % len(music_options)
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                        music_selected = (music_selected + 1) % len(music_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        choice = music_options[music_selected]
                        if choice == "Previous":
                            limusic_control.previous_track()
                        elif choice == "Play/Pause":
                            limusic_control.play_pause()
                        elif choice == "Next":
                            limusic_control.next_track()
                        elif choice == "Back":
                            view = "main"
                    elif event.key == pygame.K_ESCAPE:
                        view = "main"
                else:  # view == "main"
                    if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                        selected = (selected + (1 if event.key in (pygame.K_DOWN, pygame.K_RIGHT) else -1)) % len(options)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if options[selected] == "Resume":
                            result = "resume"
                            running = False
                        elif options[selected] == "Music":
                            view = "music"
                            last_poll = -MUSIC_POLL_MS  # force an immediate refresh
                        else:  # "Quit"
                            view = "quit_confirm"
                            options = ["Yes", "No"]
                            selected = 1  # "No" is always the default
                    elif event.key == pygame.K_ESCAPE:
                        result = "resume"
                        running = False

        if view == "music":
            now = pygame.time.get_ticks()
            if now - last_poll >= MUSIC_POLL_MS:
                last_poll = now
                music_meta = limusic_control.metadata()
                art_url = music_meta.get("art_url") if music_meta else None
                if art_url != music_art_url:
                    music_art_url = art_url
                    music_art_surface = None
                    art_path = limusic_control.fetch_art(art_url) if art_url else None
                    if art_path:
                        try:
                            image = pygame.image.load(art_path)
                            music_art_surface = pygame.transform.smoothscale(image, (ART_SIZE, ART_SIZE))
                        except pygame.error:
                            music_art_surface = None

        screen.fill(BG)
        center_x = screen.get_width() // 2

        if view == "music":
            screen.blit(font.render("Music", True, FG), (center_x - 60, 120))
            if music_art_surface is not None:
                screen.blit(music_art_surface, (center_x - ART_SIZE // 2, 170))
            text_y = 170 + ART_SIZE + 20 if music_art_surface is not None else 200
            if music_meta:
                title = music_meta["title"] or "(nothing playing)"
                screen.blit(font.render(title, True, FG), (center_x - 200, text_y))
                if music_meta["artist"]:
                    screen.blit(hint_font.render(music_meta["artist"], True, DIM), (center_x - 200, text_y + 40))
            else:
                screen.blit(hint_font.render("Limusic isn't available right now.", True, DIM), (center_x - 200, text_y))
            controls_y = text_y + 80
            for i, label in enumerate(music_options):
                color = SEL_BG if i == music_selected else BG
                rect = pygame.Rect(center_x - 300 + i * 160, controls_y, 140, 50)
                pygame.draw.rect(screen, color, rect)
                screen.blit(hint_font.render(label, True, FG), (rect.x + 15, rect.y + 15))
            screen.blit(hint_font.render("Left/Right: choose   Enter: select   Escape: back", True, DIM), (center_x - 220, controls_y + 80))
        else:
            heading = "Quit?" if view == "quit_confirm" else "Paused"
            screen.blit(font.render(heading, True, FG), (center_x - 80, 160))
            if view == "quit_confirm":
                msg = "This closes what's running right now. Any unsaved progress is lost."
                screen.blit(hint_font.render(msg, True, DIM), (center_x - 260, 220))
            for i, label in enumerate(options):
                color = SEL_BG if i == selected else BG
                x = center_x - (len(options) * 180) // 2 + i * 180
                rect = pygame.Rect(x, 280, 150, 60)
                pygame.draw.rect(screen, color, rect)
                screen.blit(font.render(label, True, FG), (rect.x + 20, rect.y + 12))
            screen.blit(hint_font.render("Left/Right: choose   Enter: select   Escape: back", True, DIM), (center_x - 220, 380))

        pygame.display.flip()
        clock.tick(30)

    with open(result_path, "w") as f:
        f.write(result)


if __name__ == "__main__":
    main()
