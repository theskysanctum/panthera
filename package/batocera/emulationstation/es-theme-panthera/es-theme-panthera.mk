################################################################################
#
# es-theme-panthera
#
################################################################################

ES_THEME_PANTHERA_VERSION = 1.0
ES_THEME_PANTHERA_LICENSE = MIT
ES_THEME_PANTHERA_SOURCE =

define ES_THEME_PANTHERA_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/emulationstation/themes/es-theme-panthera
	cp -r $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/emulationstation/es-theme-panthera/theme/* \
	    $(TARGET_DIR)/usr/share/emulationstation/themes/es-theme-panthera
endef

$(eval $(generic-package))
