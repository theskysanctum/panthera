#!/usr/bin/env python3
"""Physical disc (or any media mounted at a fixed device node) as a game source. No manifest to
author: a disc (or any folder on it) is one of three things, decided by what's actually there -

  play.txt present    -> this is a game. One line `system = <es_systems.yml key>` (blank lines
                          and #comments are ignored) says which system it's for. If exactly one
                          .m3u file also sits here, that's what gets played (RetroArch's own
                          multi-disc playlist format; every other file next to it is ignored -
                          the .m3u already lists what it needs). Otherwise there must be exactly
                          one file left once play.txt and any single obvious image (boxart, tried
                          by extension) are set aside; that file is the rom.
  no play.txt, folders -> this is a browsable collection: every subfolder is one entry (its name
                          is the label), and opening one applies the exact same three rules to it
                          - a disc can nest as many collections-of-collections as you like.
  neither               -> nothing playable here.

So a single game on the whole disc is just `play.txt` + the rom (+ optionally a cover.png) at the
root; a collection is a folder per game, each with its own play.txt; a multi-disc game is a
folder with play.txt, the .m3u and the discs it names, nothing else to think about."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEVICE_NODE = "/dev/sr0"
MOUNTPOINT = Path("/userdata/system/.disc-mount")
PLAY_FILE = "play.txt"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def mount_disc(device=DEVICE_NODE):
    """MOUNTPOINT if a disc is actually mounted there afterward, else None - no disc inserted and
    a failed mount both look the same to callers. Blocking, never raises. Already-mounted is a
    no-op (checked via findmnt rather than blindly re-mounting, which `mount` itself would just
    refuse with an error anyway)."""
    result = subprocess.run(["findmnt", "--noheadings", "--output", "SOURCE", str(MOUNTPOINT)], capture_output=True, text=True)
    if result.stdout.strip():
        return MOUNTPOINT
    MOUNTPOINT.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["mount", "-o", "ro", device, str(MOUNTPOINT)], check=True, capture_output=True)
        return MOUNTPOINT
    except subprocess.CalledProcessError:
        return None


def unmount_disc():
    result = subprocess.run(["findmnt", "--noheadings", "--output", "SOURCE", str(MOUNTPOINT)], capture_output=True, text=True)
    if not result.stdout.strip():
        return True
    try:
        subprocess.run(["umount", str(MOUNTPOINT)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def read_play_file(folder):
    """play.txt's content is the system id and nothing else - `snes`, `psx`, whatever
    es_systems.yml calls it - one line, no key or prefix. Blank lines and #comment lines are
    ignored so a disc author can still leave themselves a note; the first real line is the id.
    None if there's no play.txt or every line in it is blank/a comment."""
    path = folder / PLAY_FILE
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                return line
    except OSError:
        return None
    return None


def _find_rom(folder):
    """The one file this leaf actually plays: the folder's single .m3u if it has exactly one
    (everything else next to it is ignored on purpose), else the one plain file left once
    play.txt and a single obvious image are set aside. None when that isn't unambiguous."""
    m3u_files = sorted(folder.glob("*.m3u"))
    if len(m3u_files) == 1:
        return m3u_files[0]
    if len(m3u_files) > 1:
        return None
    candidates = [p for p in sorted(folder.iterdir()) if p.is_file() and p.name != PLAY_FILE]
    images = [p for p in candidates if p.suffix.lower() in IMAGE_EXTS]
    if len(images) == 1:
        candidates = [p for p in candidates if p not in images]
    roms = [p for p in candidates if p.suffix.lower() not in IMAGE_EXTS] or candidates
    if len(roms) != 1:
        return None
    return roms[0]


def _find_boxart(folder):
    images = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return images[0] if len(images) == 1 else None


class Entry:
    """One row of what browse() returns: either a folder to open (`kind == "folder"`) or a game
    to install (`kind == "game"`)."""

    def __init__(self, kind, name, path, system=None, rom=None, boxart=None):
        self.kind = kind
        self.name = name
        self.path = path
        self.system = system
        self.rom = rom
        self.boxart = boxart

    def __repr__(self):
        return f"Entry({self.kind!r}, {self.name!r})"


def browse(folder=None):
    """[Entry] for `folder` (the disc's root by default): one "game" entry if play.txt says this
    is a leaf (empty if the rom can't be pinned down - see _find_rom), else one "folder" entry
    per subfolder, else []. Never raises; a folder that can't even be listed (nothing mounted) is
    empty."""
    folder = Path(folder) if folder else MOUNTPOINT
    try:
        if not folder.is_dir():
            return []
        system = read_play_file(folder)
        if system is not None:
            rom = _find_rom(folder)
            if rom is None:
                return []
            return [Entry("game", folder.name or system, folder, system=system, rom=rom, boxart=_find_boxart(folder))]
        return [Entry("folder", p.name, p) for p in sorted(folder.iterdir()) if p.is_dir()]
    except OSError:
        return []


def _sanitize(name):
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip() or "game"


def install_game(entry, dest_roms_dir):
    """Copies entry's rom (and, for an .m3u, every disc it names, resolved the way RetroArch
    itself reads an .m3u: one relative path per non-empty, non-#comment line) into
    dest_roms_dir. A multi-disc game gets its own subfolder. Skips (does not overwrite) if the
    destination already exists. Returns (ok, message); never raises."""
    dest_roms_dir = Path(dest_roms_dir)
    dest_roms_dir.mkdir(parents=True, exist_ok=True)
    description = entry.name
    try:
        if entry.rom.suffix.lower() == ".m3u":
            dest_dir = dest_roms_dir / _sanitize(description)
            if dest_dir.exists():
                return False, f"{description} is already installed"
            dest_dir.mkdir(parents=True)
            discs = [line.split("#", 1)[0].strip() for line in entry.rom.read_text(encoding="utf-8", errors="replace").splitlines()]
            for rel in [d for d in discs if d]:
                shutil.copy2(entry.rom.parent / rel, dest_dir)
            shutil.copy2(entry.rom, dest_dir)
            return True, f"Installed {description}"
        dest_file = dest_roms_dir / entry.rom.name
        if dest_file.exists():
            return False, f"{description} is already installed"
        shutil.copy2(entry.rom, dest_roms_dir)
        return True, f"Installed {description}"
    except OSError as e:
        return False, f"Couldn't install {description}: {e}"


def roms_dir_for_system(system):
    return Path("/userdata/roms") / system


if __name__ == "__main__":
    # Quick manual check: `disc_content.py [folder]` prints what browse() sees there.
    for entry in browse(Path(sys.argv[1]) if len(sys.argv) > 1 else None):
        print(entry, "system=" + str(entry.system), "rom=" + str(entry.rom))
