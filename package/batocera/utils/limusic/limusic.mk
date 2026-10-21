################################################################################
#
# limusic
#
################################################################################

LIMUSIC_SOURCE =
LIMUSIC_DEPENDENCIES = podman

LIMUSIC_CONTAINER_DIR = $(BR2_EXTERNAL_BATOCERA_PATH)/containers/desktop-apps
LIMUSIC_IMAGE_TAR = $(@D)/desktop-apps.tar

# Built with the host's own podman, not cross-compiled - the same
# `podman build` the image's own README already documents as a manual
# step, just run automatically here so the result ends up embedded in
# the rootfs instead of needing that done by hand on every device. The
# resulting .tar is never committed to the repo: it lands under
# buildroot's own per-package build dir ($(@D), under output/, already
# gitignored) and from there only ever into $(TARGET_DIR), buildroot's
# rootfs staging area - the Containerfile is the only part of this that
# is source.
define LIMUSIC_BUILD_CMDS
	podman build --tag desktop-apps:latest $(LIMUSIC_CONTAINER_DIR)
	podman save --output $(LIMUSIC_IMAGE_TAR) desktop-apps:latest
endef

define LIMUSIC_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(LIMUSIC_IMAGE_TAR) $(TARGET_DIR)/usr/share/batocera/containers/desktop-apps.tar
	mkdir -p $(TARGET_DIR)/usr/share/batocera/services
	$(INSTALL) -D -m 0755 $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/limusic/limusic \
	    $(TARGET_DIR)/usr/share/batocera/services/limusic
endef

$(eval $(generic-package))
