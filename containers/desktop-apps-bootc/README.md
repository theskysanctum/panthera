# desktop-apps-bootc

Standalone, bootable version of [`../desktop-apps`](../desktop-apps): the
same openbox + picom + Brave kiosk session, but shipped as the whole OS
(a [bootc](https://containers.github.io/bootc/) image on a Fedora bootc
base) instead of a container that `container_apps` runs on top of Panthera.

This is a separate artifact from Panthera's main Buildroot image - it
doesn't touch the Batocera/EmulationStation build, and Panthera's build
doesn't produce or consume it. Use it when you want this kiosk session as
its own bootable appliance (e.g. flashed to a drive and run directly on
hardware), not as a `.capp` shortcut inside Panthera.

## Build the container image

```sh
podman build -t desktop-apps-bootc:latest -f Containerfile .
```

To point it at a different app/URL, override the kiosk command at build
time (it becomes the X session's only client, so keep it a single
foreground command):

```sh
podman build -t desktop-apps-bootc:latest \
    --build-arg KIOSK_CMD="/usr/bin/brave-browser --no-sandbox --kiosk https://your-app" \
    -f Containerfile .
```

## Build a raw disk image

Needs rootful podman and `bootc-image-builder`, which itself needs to run
privileged:

```sh
mkdir -p output
sudo podman run --rm -it --privileged \
    --pull=newer \
    --security-opt label=type:unconfined_t \
    -v ./output:/output \
    -v /var/lib/containers/storage:/var/lib/containers/storage \
    quay.io/centos-bootc/bootc-image-builder:latest \
    --type raw --local desktop-apps-bootc:latest
```

The result lands at `output/image/disk.raw` - write it to a drive with
`dd` (or an imaging tool like Raspberry Pi Imager/balenaEtcher) and boot
it directly into the kiosk session, no installer step needed.

## Design notes

- Runs as root, same reasoning as `container_apps`: this is a
  single-purpose appliance with no real multi-user boundary to protect,
  not a general-purpose desktop, so the usual argument for an unprivileged
  X session doesn't buy much here.
- `kiosk.service` replaces a display manager: it starts X directly on
  tty1 via `startx` and restarts it if the session ever exits, so there's
  nothing to log into and nothing that falls back to a login prompt.
- Updates are plain `bootc` image updates (`bootc upgrade`) against
  whatever registry `desktop-apps-bootc:latest` gets pushed to - rebuild
  the container image, push it, and running instances pull the new layer
  on their own schedule.
