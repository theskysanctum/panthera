#!/bin/bash
set -e

APP_USER=appuser

# Grant appuser rw on whatever hardware actually got passed through, via a
# per-file ACL rather than matching it into the device's owning group:
# some of these (USB bus nodes, rfkill) are root:root with no group write
# bit for anyone else to join anyway, and group-matching on an arbitrary
# host GID risks silently handing appuser membership in something
# unrelated and more sensitive (e.g. "disk") if a device happens to share
# that GID. setfacl only affects the one file.
for dev in /dev/dri/* /dev/video* /dev/input/* /dev/snd/* /dev/bus/usb/*/* /dev/rfkill; do
    [ -e "$dev" ] || continue
    setfacl -m "u:$APP_USER:rw" "$dev" || echo "entrypoint: couldn't ACL $dev, continuing" >&2
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
