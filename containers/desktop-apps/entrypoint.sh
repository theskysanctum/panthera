#!/bin/bash
set -e

APP_USER=appuser

# Host /dev nodes keep their host-side group ownership across the bind
# mount, and those GIDs vary per host - so match appuser into whatever
# groups the passed-through hardware actually belongs to, rather than
# baking in a fixed list. Root-owned (gid 0) devices need no extra group;
# everything else gets appuser added to a same-GID group, creating one
# locally if the container doesn't already have it.
for dev in /dev/dri/* /dev/video* /dev/input/* /dev/snd/* /dev/bus/usb/*/*; do
    [ -e "$dev" ] || continue
    gid=$(stat -c %g "$dev")
    [ "$gid" = "0" ] && continue
    group=$(getent group "$gid" | cut -d: -f1)
    if [ -z "$group" ]; then
        group="hostdev$gid"
        groupadd -g "$gid" "$group"
    fi
    usermod -aG "$group" "$APP_USER" >/dev/null
done

# XAUTHORITY is bind-mounted read-only from the host and typically owned by
# root (Panthera runs as root) - copy it somewhere appuser can actually
# read, since root can read it regardless of mode but appuser can't yet.
env_args=("HOME=/home/$APP_USER")
if [ -n "$XAUTHORITY" ] && [ -f "$XAUTHORITY" ]; then
    install -m 0600 -o "$APP_USER" -g "$APP_USER" "$XAUTHORITY" "/home/$APP_USER/.Xauthority"
    env_args+=("XAUTHORITY=/home/$APP_USER/.Xauthority")
fi

exec setpriv --reuid="$APP_USER" --regid="$APP_USER" --init-groups \
    env "${env_args[@]}" \
    /usr/local/bin/session.sh "$@"
