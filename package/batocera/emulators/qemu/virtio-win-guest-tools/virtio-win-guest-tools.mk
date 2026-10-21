################################################################################
#
# virtio-win-guest-tools
#
################################################################################

VIRTIO_WIN_GUEST_TOOLS_VERSION = 0.1.302-1
VIRTIO_WIN_GUEST_TOOLS_SITE = https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-$(VIRTIO_WIN_GUEST_TOOLS_VERSION)
VIRTIO_WIN_GUEST_TOOLS_SOURCE = virtio-win-gt-x64.msi
VIRTIO_WIN_GUEST_TOOLS_EXTRA_DOWNLOADS = virtio-win-gt-x86.msi
VIRTIO_WIN_GUEST_TOOLS_LICENSE = BSD-3-Clause

define VIRTIO_WIN_GUEST_TOOLS_EXTRACT_CMDS
	cp $(VIRTIO_WIN_GUEST_TOOLS_DL_DIR)/virtio-win-gt-x64.msi $(@D)
	cp $(VIRTIO_WIN_GUEST_TOOLS_DL_DIR)/virtio-win-gt-x86.msi $(@D)
endef

define VIRTIO_WIN_GUEST_TOOLS_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/virtio-win-gt-x64.msi \
	    $(TARGET_DIR)/usr/share/batocera/qemu/guest-tools/virtio-win-gt-x64.msi
	$(INSTALL) -D -m 0644 $(@D)/virtio-win-gt-x86.msi \
	    $(TARGET_DIR)/usr/share/batocera/qemu/guest-tools/virtio-win-gt-x86.msi
endef

$(eval $(generic-package))
