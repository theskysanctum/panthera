################################################################################
#
# batocera-discloader
#
################################################################################

BATOCERA_DISCLOADER_VERSION = 1.0
BATOCERA_DISCLOADER_LICENSE = GPL-3.0
BATOCERA_DISCLOADER_SOURCE =

define BATOCERA_DISCLOADER_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/batocera/discloader
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-discloader/disc_content.py \
	    $(TARGET_DIR)/usr/share/batocera/discloader/disc_content.py
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-discloader/es_notify.py \
	    $(TARGET_DIR)/usr/share/batocera/discloader/es_notify.py
	$(INSTALL) -m 0755 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-discloader/batocera-disc-install \
	    $(TARGET_DIR)/usr/bin/batocera-disc-install
endef

$(eval $(generic-package))
