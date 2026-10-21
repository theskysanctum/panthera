#!/bin/bash
set -e

openbox-session &
picom --config /etc/xdg/picom.conf --daemon || echo "entrypoint: picom didn't start, continuing without it" >&2

exec "$@"
