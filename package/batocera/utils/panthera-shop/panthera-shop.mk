################################################################################
#
# panthera-shop
#
################################################################################

PANTHERA_SHOP_VERSION = 62e8053ff1bbe5b1d063da260dc03414c8b15f36
PANTHERA_SHOP_SITE = $(call github,theskysanctum,RGSX,$(PANTHERA_SHOP_VERSION))
PANTHERA_SHOP_LICENSE = Custom (no SPDX license in upstream repo; README: "Free and open-source software. Use, modify, and distribute freely.")
PANTHERA_SHOP_DEPENDENCIES = python3 python-pygame2 python-requests

# A fork of RetroGameSets/RGSX (github.com/RetroGameSets/RGSX), a ROM downloader/content shop,
# rebranded "Game Downloader" and re-themed to the one Panthera theme (see
# package/batocera/emulationstation/es-theme-panthera), launched from the in-game Home overlay
# (batocera-home) instead of being a "Ports" entry - see home_overlay.py's "Game Downloader"
# option. Only the app itself (ports/RGSX in upstream's layout) is installed, as the "RGSX"
# subfolder its own config.py expects next to its RGSX_APP_DIR env var (get_application_root()
# walks back up from its own file location, so the subfolder name has to stay "RGSX" regardless
# of this package's own name or the app's rebranded display name).
#
# Dropped from upstream's tree: RGSX.sh (its own cross-platform launcher - home_overlay.py invokes
# __main__.py directly with the env vars below instead), vendor_darkos/ (pygame/requests fallback
# for a platform with no package manager - Panthera already has both as real packages),
# update_gamelist_windows.py (RetroBat-only) and the Windows-only binaries/scripts under
# assets/progs and assets/scripts (this is a Linux-only build). qbittorrent-nox_linux and
# qbittorrent-portable.7z are dropped too - at ~51MB combined they'd be dead weight until
# something actually wires up torrent-sourced downloads, which nothing here does yet.
define PANTHERA_SHOP_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/batocera/panthera-shop
	cp -r $(@D)/ports/RGSX $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX
	rm -rf $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/vendor
	rm -rf $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/vendor_darkos
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/RGSX.sh
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/update_gamelist_windows.py
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/scripts/rgsx_firewall_setup.ps1
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/7z.dll
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/7z.exe
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/extract-xiso_win.exe
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/ps3dec_win.exe
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/unrar.exe
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/xdvdfs.exe
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/qbittorrent-nox_linux
	rm -f $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/qbittorrent-portable.7z
	chmod +x $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/7zz
	chmod +x $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/extract-xiso_linux
	chmod +x $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/ps3dec_linux
	chmod +x $(TARGET_DIR)/usr/share/batocera/panthera-shop/RGSX/assets/progs/xdvdfs
endef

$(eval $(generic-package))
