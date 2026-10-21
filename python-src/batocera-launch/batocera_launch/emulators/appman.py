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

from typing import Final

from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_common.paths import SAVES
from batocera_launch import Command, Emulator, HotkeysContext

_APPMAN_HOME: Final = SAVES / 'appman'
_APPMAN_BIN: Final = _APPMAN_HOME / 'bin'
_APPMAN_SHARE: Final = _APPMAN_HOME / 'share'
_APPMAN_CONFIG: Final = _APPMAN_HOME / 'config'
_APPMAN_CACHE: Final = _APPMAN_HOME / 'cache'


@cached_dataclass
class Appman(Emulator):
    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        return {
            'name': 'appman',
            'keys': {'exit': ['KEY_LEFTALT', 'KEY_F4']},
        }

    @property
    def needs_mouse(self) -> bool:
        return True

    async def configure(self) -> Command:
        program = self.rom.read_text().strip()

        for directory in (_APPMAN_BIN, _APPMAN_SHARE, _APPMAN_CONFIG, _APPMAN_CACHE):
            directory.mkdir(parents=True, exist_ok=True)

        return Command(
            [_APPMAN_BIN / program],
            env={
                'XDG_BIN_HOME': _APPMAN_BIN,
                'XDG_DATA_HOME': _APPMAN_SHARE,
                'XDG_CONFIG_HOME': _APPMAN_CONFIG,
                'XDG_CACHE_HOME': _APPMAN_CACHE,
            },
        )
