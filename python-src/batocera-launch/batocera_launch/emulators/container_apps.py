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

import yaml

from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_launch import Command, Emulator, HotkeysContext

_PODMAN_BIN: Final = Path('/usr/bin/podman')
_X11_SOCKET_DIR: Final = Path('/tmp/.X11-unix')


@cached_dataclass
class ContainerApps(Emulator):
    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        return {
            'name': 'container_apps',
            'keys': {'exit': ['KEY_LEFTALT', 'KEY_F4']},
        }

    @property
    def needs_mouse(self) -> bool:
        return True

    async def configure(self) -> Command:
        spec = yaml.safe_load(self.rom.read_text())

        display = os.environ.get('DISPLAY', ':0')
        xauthority = Path(os.environ.get('XAUTHORITY', Path.home() / '.Xauthority'))

        args: list[str | Path] = [
            _PODMAN_BIN, 'run', '--rm',
            # Not a security boundary here - just a way to get Brave and
            # friends their own library stack without touching the
            # read-only system image. So give the container full access
            # to the real hardware (USB, Bluetooth, webcams, GPU) rather
            # than picking individual devices to pass through.
            '--privileged',
            '--network', 'host',
            '--ipc', 'host',
            '--pid', 'host',
            '-v', '/dev:/dev',
            '-v', '/run:/run',
            '-v', f'{_X11_SOCKET_DIR}:{_X11_SOCKET_DIR}',
            '-e', f'DISPLAY={display}',
        ]

        if xauthority.exists():
            args += ['-v', f'{xauthority}:{xauthority}', '-e', f'XAUTHORITY={xauthority}']

        args += [spec['image'], *spec['cmd']]

        return Command(args)
