################################################################################
#
# batocera-home
#
################################################################################

BATOCERA_HOME_VERSION = 1.0
BATOCERA_HOME_LICENSE = GPL-3.0
BATOCERA_HOME_SOURCE =
BATOCERA_HOME_DEPENDENCIES = python3 python-evdev python-psutil python-pygame2 python-dbus-fast python-aiohttp

define BATOCERA_HOME_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/batocera/home
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-home/home_supervisor.py \
	    $(TARGET_DIR)/usr/share/batocera/home/home_supervisor.py
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-home/home_overlay.py \
	    $(TARGET_DIR)/usr/share/batocera/home/home_overlay.py
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-home/limusic_control.py \
	    $(TARGET_DIR)/usr/share/batocera/home/limusic_control.py
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-home/es_theme.py \
	    $(TARGET_DIR)/usr/share/batocera/home/es_theme.py
endef

$(eval $(generic-package))
