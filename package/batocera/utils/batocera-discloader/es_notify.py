#!/usr/bin/env python3
"""Talks to EmulationStation's local HTTP API the same way batocera-storage-manager does: wait
for /isIdle to say true (ES only accepts these while it isn't itself mid-launch/mid-scrape),
then fire the one request. Used to tell ES a disc install changed the gamelist, or to drop a
toast telling the user a disc needs the picker."""
import time
import urllib.request

ES_API = "http://127.0.0.1:1234"
MAX_WAIT_S = 300


def _get(path):
    try:
        with urllib.request.urlopen(f"{ES_API}{path}", timeout=2) as r:
            return r.read()
    except OSError:
        return None


def _post(path, data):
    try:
        req = urllib.request.Request(f"{ES_API}{path}", data=data.encode(), method="POST")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.read()
    except OSError:
        return None


def _wait_idle():
    waited = 0
    while waited < MAX_WAIT_S:
        body = _get("/isIdle")
        if body is not None and b"true" in body:
            return True
        time.sleep(1)
        waited += 1
    return False


def reload_games():
    if _wait_idle():
        _get("/reloadgames")


def notify(message):
    if _wait_idle():
        _post("/notify", message)
