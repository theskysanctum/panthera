#!/usr/bin/env python3
"""Controls Limusic (desktop YouTube Music client - see package/batocera/utils/limusic/) from
Home's own Music view: play/pause, skip, and album art, driven entirely over the
standard org.mpris.MediaPlayer2 D-Bus interface every real media player implements (confirmed live
Limusic itself supports this - "proper MPRIS support" per its own README) - this never needs to
scrape Limusic's own UI.

Limusic runs inside the shared desktop-apps container (see limusic.mk / the "limusic" service),
not directly on the host, but it's reachable here exactly as if it were a local process: the
container shares the same D-Bus bus the host uses (both bind-mount /run/dbus and are pointed at
the same socket - see dbus.sh and the "limusic" service script), so its MPRIS name shows up on
this bus too.

Album art (mpris:artUrl) may come back as a file:// path that only exists inside the container's
own filesystem, not the host's - fetch_art() just returns None for a path it can't read, the same
as it does for a plain network failure, so a caller just shows no art rather than erroring out."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus

PLAYER_BUS_NAME = 'org.mpris.MediaPlayer2.limusic-app'
PLAYER_PATH = '/org/mpris/MediaPlayer2'
PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'
PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'
# Same bus dbus.sh points every other on-device process at - there's no separate per-user
# session bus on this system, the "session" bus is the system bus socket.
SESSION_BUS_ADDRESS = 'unix:path=/run/dbus/system_bus_socket'
ART_CACHE_PATH = Path(tempfile.gettempdir()) / 'limusic-art'


async def _call(
    member: str,
    *,
    interface: str = PLAYER_INTERFACE,
    signature: str = '',
    body: list[Any] | None = None,
) -> Any:
    """Makes one D-Bus call against Limusic's MPRIS object and disconnects - a fresh connection
    per call rather than a held-open one, since these only ever fire one at a time from a
    synchronous pygame event loop (see home_overlay.py) and never need a persistent connection."""
    bus = await MessageBus(bus_address=SESSION_BUS_ADDRESS, bus_type=BusType.SESSION).connect()
    try:
        reply = await bus.call(
            Message(
                destination=PLAYER_BUS_NAME,
                path=PLAYER_PATH,
                interface=interface,
                member=member,
                signature=signature,
                body=body or [],
            )
        )
        if reply is None or reply.message_type != MessageType.METHOD_RETURN:
            return None
        return reply.body[0] if reply.body else None
    finally:
        bus.disconnect()


def _call_sync(member: str, **kwargs: Any) -> Any:
    """Never raises - every caller here treats "Limusic isn't up yet / isn't registered on the
    bus / the bus itself isn't reachable" the same way: silently do nothing rather than crash
    Home over background music being briefly unavailable."""
    try:
        return asyncio.run(_call(member, **kwargs))
    except Exception:
        return None


def play_pause() -> None:
    _call_sync('PlayPause')


def next_track() -> None:
    _call_sync('Next')


def previous_track() -> None:
    _call_sync('Previous')


def metadata() -> dict[str, str] | None:
    """{"status", "title", "artist", "art_url"} for whatever's currently loaded, or None if
    Limusic isn't running / not yet registered on the bus / nothing is loaded. Never raises."""
    status = _call_sync('Get', interface=PROPERTIES_INTERFACE, signature='ss', body=[PLAYER_INTERFACE, 'PlaybackStatus'])
    meta = _call_sync('Get', interface=PROPERTIES_INTERFACE, signature='ss', body=[PLAYER_INTERFACE, 'Metadata'])
    if status is None or meta is None:
        return None
    meta = meta.value
    title = meta.get('xesam:title')
    artist = meta.get('xesam:artist')
    art_url = meta.get('mpris:artUrl')
    return {
        'status': status.value,
        'title': title.value if title else '',
        'artist': ', '.join(artist.value) if artist else '',
        'art_url': art_url.value if art_url else '',
    }


def fetch_art(art_url: str, cache_path: Path = ART_CACHE_PATH) -> str | None:
    """The real local file path for art_url, downloaded to cache_path first if it's a remote
    http(s) URL. None (never raises) if art_url is empty, a file:// path that isn't actually
    reachable from the host (Limusic's own filesystem is the container's, not the host's - see
    this module's own docstring), or the download fails - a caller just shows no art."""
    if not art_url:
        return None
    parsed = urlparse(art_url)
    if parsed.scheme == 'file':
        return parsed.path if Path(parsed.path).exists() else None
    if parsed.scheme not in ('http', 'https'):
        return None

    async def _download() -> None:
        async with aiohttp.ClientSession() as session, session.get(art_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            cache_path.write_bytes(await response.read())

    try:
        asyncio.run(_download())
    except Exception:
        return None
    return str(cache_path)
