################################################################################
#
# stremio
#
################################################################################

STREMIO_SOURCE =

define STREMIO_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/stremio/stremio.yml \
	    $(TARGET_DIR)/usr/share/batocera/stremio.yml
	$(INSTALL) -D -m 0755 $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/stremio/batocera-stremio \
	    $(TARGET_DIR)/usr/bin/batocera-stremio
endef

$(eval $(generic-package))
