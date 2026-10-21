################################################################################
#
# appman
#
################################################################################

APPMAN_VERSION = 720e7efdc99c5f05c25e8e79d421a3cd20d6ea5b
APPMAN_SOURCE = APP-MANAGER
APPMAN_SITE = https://raw.githubusercontent.com/ivan-hc/AM/$(APPMAN_VERSION)
APPMAN_LICENSE = GPL-3.0
APPMAN_EMULATOR_INFO = appman.emulator.yml

define APPMAN_EXTRACT_CMDS
	cp $(APPMAN_DL_DIR)/$(APPMAN_SOURCE) $(@D)
endef

define APPMAN_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/APP-MANAGER $(TARGET_DIR)/usr/bin/appman
	$(INSTALL) -D -m 0755 \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/appman/batocera-appman-update \
	    $(TARGET_DIR)/usr/bin/batocera-appman-update
	mkdir -p $(TARGET_DIR)/usr/share/emulationstation/hooks
	ln -sf /usr/bin/batocera-appman-update \
	    $(TARGET_DIR)/usr/share/emulationstation/hooks/preupdate-gamelists-appman
endef

$(eval $(generic-package))
$(eval $(emulator-info-package))
