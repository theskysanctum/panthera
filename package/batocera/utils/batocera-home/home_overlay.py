#!/usr/bin/env python3
"""Home: the Resume/Music/Quit window shown when the Home hotkey is pressed during a game (see
home_supervisor.py). Launched as its own short-lived process while the real game's whole process
tree sits SIGSTOPped - see home_supervisor.py's own module docstring for the one open question
about a second process sharing the display with a merely-frozen (not exited) one.

Its panel chrome (background frame, colors, fonts) comes from es_theme.py, which reads the same
<view name="menu"> theme colors EmulationStation's own menus draw with - see es_theme.py's module
docstring for how that's done and what it falls back to. EmulationStation's own Start/Space menu
is a separate thing (see batocera-emulationstation's GuiMenu title patch, which brands it "HOME"
too so both read as one system) - this script is only ever launched from here, during a game.

Quit asks first - SIGKILLing the whole paused process tree with no way back is the one
destructive, unrecoverable action here. Resume doesn't need to ask - there's nothing to lose by
resuming. Music opens a sub-view that controls the background Limusic player (see
limusic_control.py) rather than resuming or quitting anything.

Writes its result ("resume" or "quit") to the given file path and exits."""
import os
import subprocess
import sys

import pygame

import limusic_control
from es_theme import load_menu_theme
from home_supervisor import find_home_input_devices, wait_for_home_press

BG = (20, 20, 24)

MUSIC_POLL_MS = 1000
ART_SIZE = 160

LIMUSIC_SERVICE = "/usr/share/batocera/services/limusic"
OVERLAY_WINDOW_NAME = "batocera-home-overlay"

SHOP_DIR = "/usr/share/batocera/panthera-shop/RGSX"
SHOP_SAVE_DIR = "/userdata/saves/panthera-shop"

HINT = "Left/Right: choose   Enter: select   Escape: back"


def _open_limusic_window():
    """Raises Limusic's own window on top of this one (see the "limusic" service's show/hide
    subcommands) and blocks until the Home button/key is pressed again, then hides it and
    refocuses this window.

    Once Limusic has X focus, this process's own pygame event loop stops receiving key presses -
    so the wait below reuses home_supervisor's raw evdev read of the Home button itself, the
    same one that works regardless of which window currently has focus. Like home_supervisor's
    own "share the display with a merely-frozen process" assumption (see its module docstring),
    getting keyboard focus back afterwards via xdotool windowactivate, with no window manager
    running, is the one part of this that hasn't been exercised on real hardware.
    """
    subprocess.run([LIMUSIC_SERVICE, "show"], check=False)
    wait_for_home_press(find_home_input_devices(), lambda: True)
    subprocess.run([LIMUSIC_SERVICE, "hide"], check=False)
    subprocess.run(["xdotool", "search", "--name", OVERLAY_WINDOW_NAME, "windowactivate"], check=False)


def _open_shop():
    """Launches Game Downloader (a fork of RGSX, see panthera-shop) as its own fullscreen pygame
    app, blocking until it exits and then returning to this overlay's main view - the same
    blocking-subprocess shape home_supervisor.py already uses to run this overlay itself.

    The env vars switch RGSX's own config.py into its "Docker mode" path resolution so its code
    (read-only, under /usr/share) and its mutable state (settings/history/database, writable)
    don't have to live next to each other the way its traditional <USERDATA>/roms/ports/RGSX
    layout assumes - this never runs from Ports."""
    env = dict(os.environ)
    env["RGSX_APP_DIR"] = os.path.dirname(SHOP_DIR)
    env["RGSX_CONFIG_DIR"] = SHOP_SAVE_DIR
    env["RGSX_DATA_DIR"] = "/userdata"
    subprocess.run(["python3", "__main__.py"], cwd=SHOP_DIR, env=env, check=False)


def _load_frame(theme):
    """The theme's nine-patch menu panel image, tinted by its menu background color - the same
    way ES's own NinePatchComponent tints theme->Background.path. A pure-white tint (ES's own
    untouched default) leaves the image exactly as drawn, since multiplying by white is a no-op."""
    image = pygame.image.load(str(theme.frame_path)).convert_alpha()
    if theme.background_color != (255, 255, 255, 255):
        image.fill(theme.background_color, special_flags=pygame.BLEND_RGBA_MULT)
    return image


def _ninepatch_corner(image, theme):
    if theme.corner_size:
        return theme.corner_size
    w, h = image.get_size()
    return (w // 3, h // 3)


def draw_ninepatch(screen, image, corner, rect):
    cw, ch = corner
    iw, ih = image.get_size()
    cw = max(0, min(cw, iw // 2 - 1 if iw > 2 else 0))
    ch = max(0, min(ch, ih // 2 - 1 if ih > 2 else 0))
    x, y, w, h = rect
    dw, dh = max(w - 2 * cw, 0), max(h - 2 * ch, 0)

    slices = (
        # (source rect, dest rect)
        ((0, 0, cw, ch), (x, y, cw, ch)),
        ((cw, 0, iw - 2 * cw, ch), (x + cw, y, dw, ch)),
        ((iw - cw, 0, cw, ch), (x + w - cw, y, cw, ch)),
        ((0, ch, cw, ih - 2 * ch), (x, y + ch, cw, dh)),
        ((cw, ch, iw - 2 * cw, ih - 2 * ch), (x + cw, y + ch, dw, dh)),
        ((iw - cw, ch, cw, ih - 2 * ch), (x + w - cw, y + ch, cw, dh)),
        ((0, ih - ch, cw, ch), (x, y + h - ch, cw, ch)),
        ((cw, ih - ch, iw - 2 * cw, ch), (x + cw, y + h - ch, dw, ch)),
        ((iw - cw, ih - ch, cw, ch), (x + w - cw, y + h - ch, cw, ch)),
    )
    for (sx, sy, sw, sh), (dx, dy, ddw, ddh) in slices:
        if sw <= 0 or sh <= 0 or ddw <= 0 or ddh <= 0:
            continue
        patch = image.subsurface(pygame.Rect(sx, sy, sw, sh))
        if (ddw, ddh) != (sw, sh):
            patch = pygame.transform.smoothscale(patch, (ddw, ddh))
        screen.blit(patch, (dx, dy))


def wrap_text(text, font, max_width):
    lines = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_title(screen, rect, text, font, theme, pad):
    title_h = font.get_height() + pad * 2
    surf = font.render(text.upper(), True, theme.title_color[:3])
    screen.blit(surf, (rect.centerx - surf.get_width() // 2, rect.y + pad))
    line_y = rect.y + title_h
    pygame.draw.line(screen, theme.text_color[:3], (rect.x + pad, line_y), (rect.right - pad, line_y))
    return title_h


def draw_rows(screen, rect, top, options, selected, font, theme, pad):
    row_h = font.get_height() + pad * 2
    y = top
    for i, label in enumerate(options):
        if i == selected:
            pygame.draw.rect(screen, theme.text_selector_color[:3], (rect.x, y, rect.width, row_h))
            color = theme.text_selected_color[:3]
        else:
            color = theme.text_color[:3]
        surf = font.render(label, True, color)
        screen.blit(surf, (rect.x + pad * 2, y + pad))
        y += row_h
    return y


def draw_button_row(screen, rect, top, labels, selected, font, theme, pad):
    btn_h = font.get_height() + pad * 2
    n = len(labels)
    btn_w = (rect.width - pad * (n + 1)) // n
    x = rect.x + pad
    for i, label in enumerate(labels):
        btn_rect = pygame.Rect(x, top, btn_w, btn_h)
        if i == selected:
            pygame.draw.rect(screen, theme.text_selector_color[:3], btn_rect, border_radius=btn_h // 2)
            color = theme.text_selected_color[:3]
        else:
            pygame.draw.rect(screen, theme.text_color[:3], btn_rect, width=2, border_radius=btn_h // 2)
            color = theme.text_color[:3]
        surf = font.render(label, True, color)
        screen.blit(surf, (btn_rect.centerx - surf.get_width() // 2, btn_rect.centery - surf.get_height() // 2))
        x += btn_w + pad
    return top + btn_h


def draw_footer(screen, rect, bottom, text, font, theme):
    surf = font.render(text, True, theme.footer_color[:3])
    screen.blit(surf, (rect.centerx - surf.get_width() // 2, bottom))


def panel_rect(screen, width_frac, height):
    w = int(screen.get_width() * width_frac)
    x = (screen.get_width() - w) // 2
    y = (screen.get_height() - height) // 2
    return pygame.Rect(x, y, w, height)


def main():
    result_path = sys.argv[1]
    # pids (sys.argv[2]) aren't used by this minimal overlay - kept in the argv shape anyway so a
    # future per-emulator Home action (e.g. a save-state key injected via uinput) has them
    # without changing how home_supervisor.py invokes this.

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption(OVERLAY_WINDOW_NAME)
    pygame.mouse.set_visible(False)

    theme = load_menu_theme()
    min_dim = min(screen.get_width(), screen.get_height())
    font_path = str(theme.font_path) if theme.font_path else None
    title_font = pygame.font.Font(font_path, int(min_dim * 0.085))
    text_font = pygame.font.Font(font_path, int(min_dim * 0.045))
    footer_font = pygame.font.Font(font_path, int(min_dim * 0.035))
    pad = max(4, int(min_dim * 0.012))

    frame_image = _load_frame(theme)
    frame_corner = _ninepatch_corner(frame_image, theme)

    view = "main"  # "main" | "quit_confirm" | "music"
    options = ["Resume", "Music", "Game Downloader", "Quit"]
    selected = 0
    clock = pygame.time.Clock()
    result = "resume"

    music_options = ["Previous", "Play/Pause", "Next", "Open", "Back"]
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
                            options = ["Resume", "Music", "Game Downloader", "Quit"]
                            selected = 0
                    elif event.key == pygame.K_ESCAPE:
                        view = "main"
                        options = ["Resume", "Music", "Game Downloader", "Quit"]
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
                        elif choice == "Open":
                            _open_limusic_window()
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
                        elif options[selected] == "Game Downloader":
                            _open_shop()
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

        if view == "quit_confirm":
            msg = "This closes what's running right now. Any unsaved progress is lost."
            panel_w_frac = 0.46
            msg_lines = wrap_text(msg, footer_font, int(screen.get_width() * panel_w_frac) - pad * 4)
            title_h = title_font.get_height() + pad * 2
            msg_h = len(msg_lines) * (footer_font.get_height() + pad // 2) + pad
            btn_h = text_font.get_height() + pad * 2
            panel_h = title_h + msg_h + btn_h + pad * 2
            rect = panel_rect(screen, panel_w_frac, panel_h)
            draw_ninepatch(screen, frame_image, frame_corner, rect)
            draw_title(screen, rect, "Quit?", title_font, theme, pad)

            y = rect.y + title_h + pad
            for line in msg_lines:
                surf = footer_font.render(line, True, theme.text_color[:3])
                screen.blit(surf, (rect.centerx - surf.get_width() // 2, y))
                y += footer_font.get_height() + pad // 2

            draw_button_row(screen, rect, y + pad // 2, options, selected, text_font, theme, pad)
            draw_footer(screen, rect, rect.bottom + pad, HINT, footer_font, theme)

        elif view == "music":
            panel_w_frac = 0.62
            title_h = title_font.get_height() + pad * 2
            content_h = ART_SIZE + pad if music_art_surface is not None else 0
            content_h += (text_font.get_height() + footer_font.get_height() + pad * 3)
            btn_h = footer_font.get_height() + pad * 2
            panel_h = title_h + content_h + btn_h + pad * 2
            rect = panel_rect(screen, panel_w_frac, panel_h)
            draw_ninepatch(screen, frame_image, frame_corner, rect)
            draw_title(screen, rect, "Music", title_font, theme, pad)

            y = rect.y + title_h + pad
            if music_art_surface is not None:
                screen.blit(music_art_surface, (rect.centerx - ART_SIZE // 2, y))
                y += ART_SIZE + pad

            if music_meta:
                title_text = music_meta["title"] or "(nothing playing)"
                surf = text_font.render(title_text, True, theme.text_color[:3])
                screen.blit(surf, (rect.centerx - surf.get_width() // 2, y))
                y += text_font.get_height() + pad // 2
                if music_meta["artist"]:
                    surf = footer_font.render(music_meta["artist"], True, theme.footer_color[:3])
                    screen.blit(surf, (rect.centerx - surf.get_width() // 2, y))
                    y += footer_font.get_height() + pad // 2
            else:
                surf = footer_font.render("Limusic isn't available right now.", True, theme.footer_color[:3])
                screen.blit(surf, (rect.centerx - surf.get_width() // 2, y))
                y += footer_font.get_height() + pad // 2

            draw_button_row(screen, rect, y + pad // 2, music_options, music_selected, footer_font, theme, pad)
            draw_footer(screen, rect, rect.bottom + pad, HINT, footer_font, theme)

        else:  # view == "main"
            panel_w_frac = 0.4
            title_h = title_font.get_height() + pad * 2
            row_h = text_font.get_height() + pad * 2
            panel_h = title_h + row_h * len(options) + pad
            rect = panel_rect(screen, panel_w_frac, panel_h)
            draw_ninepatch(screen, frame_image, frame_corner, rect)
            draw_title(screen, rect, "Home", title_font, theme, pad)
            draw_rows(screen, rect, rect.y + title_h, options, selected, text_font, theme, pad)
            draw_footer(screen, rect, rect.bottom + pad, HINT, footer_font, theme)

        pygame.display.flip()
        clock.tick(30)

    with open(result_path, "w") as f:
        f.write(result)


if __name__ == "__main__":
    main()
