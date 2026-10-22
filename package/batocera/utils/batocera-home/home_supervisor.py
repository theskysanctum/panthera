#!/usr/bin/env python3
"""Supervises a running game/emulator process: watches for the Home hotkey - the gamepad's
Guide/Mode button (BTN_MODE) or the keyboard's Home key, whichever's actually connected - for as
long as it runs. On trigger: SIGSTOPs the whole process tree (found via psutil, since the pid
batocera-launch starts is often a wrapper script, not the real emulator binary) and shows
home_overlay.py's Resume/Quit window. Resume SIGCONTs everything back; Quit SIGKILLs the whole
tree outright rather than trying a graceful SIGTERM first - a stopped process can't run a SIGTERM
handler anyway (it would just sit queued until resumed).

Gamepad/keyboard detection reads /dev/input/event* directly via evdev rather than going through
evmapy/hotkeygen's own translation layer: this needs the raw Guide/Home press itself (to decide
*whether* to pause), not a key already remapped for some other purpose, and it has to keep
watching the whole time the game runs, independently of whatever hotkey config that game's own
system has.

*** The overlay step (show_home_overlay() below) is the one piece of this file that hasn't been
verified on real hardware: it assumes a second process can still acquire the display while the
first one is merely SIGSTOPped (not exited), which holds on an X11/Wayland session but is genuinely
unconfirmed on a plain KMS/DRM one, where the stopped emulator may still hold the DRM master lease.
If that turns out not to work on a given target, the fallback is to switch to a spare VT before
drawing the overlay and switch back on resume, rather than trying to share the game's own display
context - everything else here (the SIGSTOP/SIGCONT engine, the pause-button watch) doesn't depend
on that part and is safe to rely on regardless. ***
"""
import os
import select
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import psutil
from evdev import InputDevice, ecodes, list_devices

HOME_OVERLAY = str(Path(__file__).resolve().parent / "home_overlay.py")
HOME_BUTTON = ecodes.BTN_MODE
HOME_KEY = ecodes.KEY_HOME  # keyboard equivalent - useful with no gamepad connected too


def find_home_input_devices():
    """Every /dev/input/event* device that can report BTN_MODE or KEY_HOME - gamepads and
    keyboards alike, whatever's actually plugged in. Never raises; a device that disappears or
    can't be opened (permissions, unplugged mid-scan) is just skipped."""
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities().get(ecodes.EV_KEY, [])
            if HOME_BUTTON in caps or HOME_KEY in caps:
                devices.append(dev)
        except OSError:
            continue
    return devices


def process_tree_pids(root_pid):
    try:
        root = psutil.Process(root_pid)
    except psutil.NoSuchProcess:
        return []
    return [root_pid] + [p.pid for p in root.children(recursive=True)]


def send_signal(pids, sig):
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


def wait_for_home_press(devices, is_running, poll_timeout=0.3):
    """Blocks until either the Home button/key is pressed (True) or is_running() goes false,
    meaning the game exited on its own while nobody opened Home (False)."""
    device_by_fd = {d.fd: d for d in devices}
    while is_running():
        if not device_by_fd:
            return False
        ready, _, _ = select.select(device_by_fd, [], [], poll_timeout)
        for fd in ready:
            try:
                for event in device_by_fd[fd].read():
                    if event.type == ecodes.EV_KEY and event.code in (HOME_BUTTON, HOME_KEY) and event.value == 1:
                        return True
            except OSError:
                del device_by_fd[fd]
    return False


def show_home_overlay(env, pids):
    """Runs home_overlay.py as its own short-lived process, passing the frozen process tree's
    pids as argv (it needs them to do its own brief SIGCONT/inject-key/SIGSTOP round-trip for
    whichever action gets chosen) and reads back its one-word result ("resume" or "quit") from a
    temp file, the same hand-off shape as the game-launch side already uses for small one-shot
    subprocess results."""
    fd, result_path = tempfile.mkstemp(prefix="home-result-")
    os.close(fd)
    try:
        subprocess.run(["python3", HOME_OVERLAY, result_path, ",".join(str(pid) for pid in pids)], env=env)
        with open(result_path) as f:
            return f.read().strip() or "resume"
    finally:
        if os.path.exists(result_path):
            os.remove(result_path)


def supervise(pid, env=None):
    """Call this with the real, already-running game/emulator's root pid. Blocks until that
    process tree exits (whether on its own, or because Quit was chosen from Home).
    Safe to call with no gamepad/keyboard found at all - Home is then just unavailable for this
    session, same as running with no supervisor at all."""
    env = env if env is not None else dict(os.environ)
    devices = find_home_input_devices()

    def is_running():
        return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE

    if not devices:
        while is_running():
            try:
                os.waitpid(pid, 0)
                return
            except ChildProcessError:
                return

    while True:
        pressed = wait_for_home_press(devices, is_running)
        if not is_running():
            return
        if not pressed:
            continue

        pids = process_tree_pids(pid)
        send_signal(pids, signal.SIGSTOP)
        choice = show_home_overlay(env, pids)
        if choice == "quit":
            send_signal(pids, signal.SIGKILL)
            return
        send_signal(pids, signal.SIGCONT)


if __name__ == "__main__":
    # Manual test: `home_supervisor.py <pid>` supervises an already-running process by hand.
    supervise(int(sys.argv[1]))
