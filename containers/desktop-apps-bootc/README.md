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

## Editing with Bootc Studio

This Containerfile is structured for [Bootc Studio](https://github.com/theskysanctum/bootc-studio):
open this directory there and its Packages tab can add/remove dnf
packages, COPR repos, Flatpaks or AppMan apps without hand-editing the
file - everything else here (the brave repo bootstrap, user/systemd
setup) is plain hand-written content outside the tool's marked blocks,
left untouched either way. It also drives the rest of this README's
pipeline (build/lint/VM test/ISO) from one place instead of the raw
commands below.

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
    --type qcow2 --rootfs xfs --local desktop-apps-bootc:latest
```

The result lands at `output/qcow2/disk.qcow2` - boot it directly with
QEMU/KVM (`-drive file=output/qcow2/disk.qcow2,format=qcow2,if=virtio`),
or convert it to a flashable raw disk first if you need to write it to
physical media:

```sh
qemu-img convert -O raw output/qcow2/disk.qcow2 output/disk.raw
```

`--type qcow2` instead of `--type raw` keeps the build output small
enough to pass around (qcow2's own sparse+compressed format vs. a 10GB
raw file) - this isn't something that belongs in git either way (not
committed, see `.gitignore`), just a local build artifact.

## Design notes

- Runs as a real non-root user (`kiosk`), not root: Chromium (and GUI apps
  generally) refuse their own sandbox when running as root, so rather than
  work around that with `--no-sandbox`, the session just isn't root.
  `kiosk` is in the `video`/`audio`/`input`/`render` groups so the browser
  can actually use the hardware this image installed drivers for.
- `kiosk.service` replaces a display manager: `User=`/`PAMName=login` get
  it a real logind session on tty1, it starts X directly via `startx`, and
  restarts if the session ever exits - so there's nothing to log into and
  nothing that falls back to a login prompt.
- Updates are plain `bootc` image updates (`bootc upgrade`) against
  whatever registry `desktop-apps-bootc:latest` gets pushed to - rebuild
  the container image, push it, and running instances pull the new layer
  on their own schedule.
