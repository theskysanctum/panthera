#!/bin/bash
set -e

openbox-session &
picom --config /etc/xdg/picom.conf --daemon

exec "$@"
