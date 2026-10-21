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

import os
from pathlib import Path
from typing import Final

from batocera_common.asyncio import run
from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_launch import Command, Emulator, HotkeysContext

_QEMU_BIN: Final = Path('/usr/bin/qemu-system-x86_64')
_QEMU_IMG_BIN: Final = Path('/usr/bin/qemu-img')
_KVM_DEVICE: Final = Path('/dev/kvm')

_DISK_SIZE: Final = '32G'
_RAW_EXTENSIONS: Final = {'.img', '.raw'}


def _kvm_available() -> bool:
    return _KVM_DEVICE.exists() and os.access(_KVM_DEVICE, os.R_OK | os.W_OK)


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

        if self.rom.suffix.lower() == '.iso':
            disk = self.saves_dir / f'{self.rom.stem}.qcow2'
            if not disk.exists():
                disk.parent.mkdir(parents=True, exist_ok=True)
                await run(_QEMU_IMG_BIN, 'create', '-f', 'qcow2', disk, _DISK_SIZE)

            boot_order = 'd' if self.config.get_str('qemu_boot', 'disk') == 'cdrom' else 'c'
            args += [
                '-cdrom', self.rom,
                '-drive', f'file={disk},if=virtio,format=qcow2',
                '-boot', f'order={boot_order}',
            ]
        else:
            disk_format = 'raw' if self.rom.suffix.lower() in _RAW_EXTENSIONS else 'qcow2'
            args += ['-drive', f'file={self.rom},if=virtio,format={disk_format}']

        return Command(args)
