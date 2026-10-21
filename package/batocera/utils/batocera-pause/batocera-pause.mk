################################################################################
#
# batocera-pause
#
################################################################################

BATOCERA_PAUSE_VERSION = 1.0
BATOCERA_PAUSE_LICENSE = GPL-3.0
BATOCERA_PAUSE_SOURCE =
BATOCERA_PAUSE_DEPENDENCIES = python3 python-evdev python-psutil python-pygame2 python-dbus-fast python-aiohttp

define BATOCERA_PAUSE_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/batocera/pause
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-pause/pause_supervisor.py \
	    $(TARGET_DIR)/usr/share/batocera/pause/pause_supervisor.py
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-pause/pause_overlay.py \
	    $(TARGET_DIR)/usr/share/batocera/pause/pause_overlay.py
	$(INSTALL) -m 0644 -D \
	    $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/utils/batocera-pause/limusic_control.py \
	    $(TARGET_DIR)/usr/share/batocera/pause/limusic_control.py
endef

$(eval $(generic-package))
