# This file is part of The Batocera Linux Distribution (https://batocera.org).
# Copyright (c) 2026 The Batocera Team.
#
# The Batocera Linux Distribution is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# The Batocera Linux Distribution is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with The Batocera Linux Distribution. If not, see
# <https://www.gnu.org/licenses/>.
#
# YOU MUST RETAIN THE LICENSE AND COPYRIGHT NOTICES ABOVE IN ANY
# REDISTRIBUTED VERSION OF THIS FILE.

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import yaml

from batocera_common.asyncio import run
from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_common.paths import ROMS
from batocera_launch import Command, Emulator, HotkeysContext

if TYPE_CHECKING:
    from collections.abc import Coroutine

_logger: Final = logging.getLogger(__name__)

_QEMU_BIN: Final = Path('/usr/bin/qemu-system-x86_64')
_QEMU_IMG_BIN: Final = Path('/usr/bin/qemu-img')
_KVM_DEVICE: Final = Path('/dev/kvm')

_INSTALLED_DISKS_DIR: Final = ROMS / 'os_hdds'
_DISK_SIZE: Final = '32G'
_RAW_EXTENSIONS: Final = {'.img', '.raw'}

# Windows has no inbox virtio-blk driver, so installs need a bus their
# installer media can actually see: plain IDE for XP (no inbox AHCI driver
# either), AHCI (inbox since Vista) for 7/10. Anything else defaults to virtio.
_CORE_DISK_BUS: Final = {'winxp': 'ide', 'win7': 'ahci', 'win10': 'ahci'}

# Guest Tools MSIs (VirtIO drivers + qemu-guest-agent + SPICE vdagent), exposed
# to Windows guests as a small virtual USB drive so they can be installed
# without needing a second virtual disk/ISO.
_GUEST_TOOLS_DIR: Final = Path('/usr/share/batocera/qemu/guest-tools')

# Only one qemu VM is ever launched at a time, so fixed paths are fine.
_QGA_SOCKET: Final = Path('/tmp/batocera-qemu-vm-apps.qga.sock')
_QMP_SOCKET: Final = Path('/tmp/batocera-qemu-vm-apps.qmp.sock')

_GUEST_AGENT_BOOT_TIMEOUT: Final = 180.0
_GUEST_AGENT_RETRY_INTERVAL: Final = 2.0
_GUEST_EXEC_POLL_INTERVAL: Final = 2.0
_GUEST_SHUTDOWN_GRACE: Final = 30.0

# Keeps references to the fire-and-forget supervisor tasks so they aren't
# garbage-collected while still running.
_background_tasks: Final[set[asyncio.Task[None]]] = set()


def _kvm_available() -> bool:
    return _KVM_DEVICE.exists() and os.access(_KVM_DEVICE, os.R_OK | os.W_OK)


def _disk_args(bus: str, path: Path, disk_format: str, drive_id: str, /) -> list[str | Path]:
    if bus == 'ahci':
        return [
            '-device', f'ahci,id={drive_id}-ahci',
            '-drive', f'if=none,id={drive_id},file={path},format={disk_format}',
            '-device', f'ide-hd,bus={drive_id}-ahci.0,drive={drive_id}',
        ]
    return ['-drive', f'file={path},if={bus},format={disk_format}']


def _guest_tools_args(core: str, /) -> list[str | Path]:
    if core not in _CORE_DISK_BUS:
        return []
    return [
        '-drive', f'file=fat:ro:{_GUEST_TOOLS_DIR},format=raw,if=none,id=guesttools',
        '-device', 'usb-storage,drive=guesttools',
    ]


def _vm_app_control_args() -> list[str | Path]:
    for sock in (_QGA_SOCKET, _QMP_SOCKET):
        sock.unlink(missing_ok=True)

    return [
        '-chardev', f'socket,path={_QGA_SOCKET},server=on,wait=off,id=qga0',
        '-device', 'virtio-serial',
        '-device', 'virtserialport,chardev=qga0,name=org.qemu.guest_agent.0',
        '-qmp', f'unix:{_QMP_SOCKET},server=on,wait=off',
    ]


def _spawn(coro: Coroutine[Any, Any, None], /) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _connect_unix_retrying(
    path: Path, /, *, timeout: float
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    last_error: OSError | None = None

    while loop.time() < deadline:
        try:
            return await asyncio.open_unix_connection(path)
        except OSError as e:
            last_error = e
            await asyncio.sleep(0.5)

    raise TimeoutError(f'Could not connect to {path}') from last_error


async def _read_json_line(reader: asyncio.StreamReader, /) -> dict[str, Any]:
    line = await reader.readline()
    if not line:
        raise ConnectionError('connection closed')
    return json.loads(line)


async def _send_json_line(writer: asyncio.StreamWriter, message: dict[str, Any], /) -> None:
    writer.write(json.dumps(message).encode() + b'\n')
    await writer.drain()


async def _qmp_command(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, command: dict[str, Any], /
) -> dict[str, Any]:
    await _send_json_line(writer, command)

    while True:
        message = await _read_json_line(reader)
        if 'event' not in message:
            return message


async def _qmp_open(path: Path, /, *, timeout: float) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    reader, writer = await _connect_unix_retrying(path, timeout=timeout)
    await _read_json_line(reader)  # greeting
    await _qmp_command(reader, writer, {'execute': 'qmp_capabilities'})
    return reader, writer


async def _wait_for_guest_agent(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, /, *, timeout: float
) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        try:
            await _send_json_line(writer, {'execute': 'guest-ping'})
            await asyncio.wait_for(_read_json_line(reader), timeout=_GUEST_AGENT_RETRY_INTERVAL)
            return True
        except (OSError, ConnectionError, TimeoutError, json.JSONDecodeError):
            await asyncio.sleep(_GUEST_AGENT_RETRY_INTERVAL)

    return False


async def _supervise_vm_app(exe: str, exe_args: list[str], /) -> None:
    try:
        qga_reader, qga_writer = await _connect_unix_retrying(_QGA_SOCKET, timeout=30.0)

        if not await _wait_for_guest_agent(qga_reader, qga_writer, timeout=_GUEST_AGENT_BOOT_TIMEOUT):
            _logger.warning('qemu vm_apps: guest agent never answered, giving up on auto-launch')
            return

        exec_response = await _qmp_command(  # QGA shares the same request/response framing as QMP
            qga_reader,
            qga_writer,
            {'execute': 'guest-exec', 'arguments': {'path': exe, 'arg': exe_args, 'capture-output': False}},
        )
        pid = exec_response['return']['pid']

        while True:
            await asyncio.sleep(_GUEST_EXEC_POLL_INTERVAL)
            status = await _qmp_command(
                qga_reader, qga_writer, {'execute': 'guest-exec-status', 'arguments': {'pid': pid}}
            )
            if status['return'].get('exited'):
                break

        qmp_reader, qmp_writer = await _qmp_open(_QMP_SOCKET, timeout=10.0)
        await _qmp_command(qmp_reader, qmp_writer, {'execute': 'system_powerdown'})

        await asyncio.sleep(_GUEST_SHUTDOWN_GRACE)
        with contextlib.suppress(OSError, ConnectionError):
            await _qmp_command(qmp_reader, qmp_writer, {'execute': 'quit'})
    except Exception:
        _logger.exception('qemu vm_apps: supervising the guest application failed')


@cached_dataclass
class Qemu(Emulator):
    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        return {
            'name': 'qemu',
            'keys': {'exit': ['KEY_LEFTALT', 'KEY_F4']},
        }

    @property
    def needs_mouse(self) -> bool:
        return True

    async def configure(self) -> Command:
        accel = self.config.get_str('qemu_accel', 'auto')
        if accel == 'auto':
            accel = 'kvm' if _kvm_available() else 'tcg'

        vga = self.config.get_str('qemu_display', 'std')

        args: list[str | Path] = [
            _QEMU_BIN,
            '-m', str(self.config.get_int('qemu_ram', 2048)),
            '-smp', str(self.config.get_int('qemu_cpus', 2)),
            '-vga', vga,
            '-display', 'sdl,gl=on' if vga == 'virtio' else 'sdl',
            '-usb',
            '-device', 'usb-tablet',
            '-netdev', 'user,id=net0',
            '-device', 'virtio-net-pci,netdev=net0',
            '-cpu', 'host' if accel == 'kvm' else 'max',
        ]

        if accel == 'kvm':
            args.append('-enable-kvm')

        if self.system == 'vm_apps':
            spec = yaml.safe_load(self.rom.read_text())
            core = spec['core']
            disk = _INSTALLED_DISKS_DIR / spec['disk']
            disk_format = 'raw' if disk.suffix.lower() in _RAW_EXTENSIONS else 'qcow2'

            args += _guest_tools_args(core)
            args += _vm_app_control_args()
            args += _disk_args(_CORE_DISK_BUS.get(core, 'virtio'), disk, disk_format, 'osdisk')

            _spawn(_supervise_vm_app(spec['exe'], spec.get('args', [])))

            return Command(args)

        bus = _CORE_DISK_BUS.get(self.core, 'virtio')
        args += _guest_tools_args(self.core)

        if self.system == 'os_install':
            disk = _INSTALLED_DISKS_DIR / f'{self.rom.stem}.qcow2'
            if not disk.exists():
                disk.parent.mkdir(parents=True, exist_ok=True)
                await run(_QEMU_IMG_BIN, 'create', '-f', 'qcow2', disk, _DISK_SIZE)

            args += ['-cdrom', self.rom, '-boot', 'order=d']
            args += _disk_args(bus, disk, 'qcow2', 'osdisk')
        else:
            disk_format = 'raw' if self.rom.suffix.lower() in _RAW_EXTENSIONS else 'qcow2'
            args += _disk_args(bus, self.rom, disk_format, 'osdisk')

        return Command(args)
