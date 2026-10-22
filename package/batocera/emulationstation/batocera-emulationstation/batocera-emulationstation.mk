################################################################################
#
# batocera-emulationstation
#
################################################################################
# Last update: Commits on Oct 20, 2026
BATOCERA_EMULATIONSTATION_VERSION = 7e3e8cc735464ba258486963ba084f72fc87d898
BATOCERA_EMULATIONSTATION_SITE = https://github.com/batocera-linux/batocera-emulationstation
BATOCERA_EMULATIONSTATION_SITE_METHOD = git
BATOCERA_EMULATIONSTATION_LICENSE = MIT
BATOCERA_EMULATIONSTATION_GIT_SUBMODULES = YES
BATOCERA_EMULATIONSTATION_LICENSE = MIT, Apache-2.0
BATOCERA_EMULATIONSTATION_DEPENDENCIES = sdl2 sdl2_mixer vlc libfreeimage freetype alsa-lib
BATOCERA_EMULATIONSTATION_DEPENDENCIES += libcurl rapidjson batocera-es-system host-gettext libfribidi
# install in staging for debugging (gdb)
BATOCERA_EMULATIONSTATION_INSTALL_STAGING = YES
BATOCERA_EMULATIONSTATION_INSTALL_IMAGES = YES
# BATOCERA_EMULATIONSTATION_OVERRIDE_SRCDIR = /sources/batocera-emulationstation

BATOCERA_EMULATIONSTATION_CONF_OPTS += \
    -DCMAKE_CXX_FLAGS=-D$(call UPPERCASE,$(BATOCERA_ARCH))

ifeq ($(BR2_PACKAGE_XAPP_XINIT),y)
BATOCERA_EMULATIONSTATION_DEPENDENCIES += xapp_xinit
endif

ifeq ($(BR2_PACKAGE_HAS_LIBMALI),y)
BATOCERA_EMULATIONSTATION_DEPENDENCIES += libmali
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DCMAKE_EXE_LINKER_FLAGS=-lmali
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DCMAKE_SHARED_LINKER_FLAGS=-lmali
endif

ifeq ($(BR2_PACKAGE_HAS_LIBGL)$(BR2_PACKAGE_BATOCERA_TARGET_X86_ANY),yy)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DGL=ON
else ifeq ($(BR2_PACKAGE_BATOCERA_GLES3),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DGLES3=ON
else ifeq ($(BR2_PACKAGE_HAS_LIBGLES),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DGLES2=ON
endif

ifeq ($(BR2_PACKAGE_ESPEAK),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DENABLE_TTS=ON
BATOCERA_EMULATIONSTATION_DEPENDENCIES += espeak
endif

ifeq ($(BR2_PACKAGE_KODI)$(BR2_PACKAGE_KODI21),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DDISABLE_KODI=OFF
else
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DDISABLE_KODI=ON
endif

ifeq ($(BR2_PACKAGE_PULSEAUDIO_ENABLE_ATOMIC),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DENABLE_PULSE=ON
else
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DENABLE_PULSE=OFF
endif

ifeq ($(BR2_PACKAGE_XORG7),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DENABLE_FILEMANAGER=ON
else
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DENABLE_FILEMANAGER=OFF
endif

BATOCERA_EMULATIONSTATION_CONF_OPTS += -DBATOCERA=ON

BATOCERA_EMULATIONSTATION_KEY_SCREENSCRAPER_DEV_LOGIN=\
    $(shell grep -E '^SCREENSCRAPER_DEV_LOGIN=' \
	$(BATOCERA_EMULATIONSTATION_PKGDIR)/keys.txt | cut -d = -f 2-)
BATOCERA_EMULATIONSTATION_KEY_GAMESDB_APIKEY=\
    $(shell grep -E '^GAMESDB_APIKEY=' \
	$(BATOCERA_EMULATIONSTATION_PKGDIR)/keys.txt | cut -d = -f 2-)
BATOCERA_EMULATIONSTATION_KEY_CHEEVOS_DEV_LOGIN=\
    $(shell grep -E '^CHEEVOS_DEV_LOGIN=' \
	$(BATOCERA_EMULATIONSTATION_PKGDIR)/keys.txt | cut -d = -f 2-)
BATOCERA_EMULATIONSTATION_KEY_HFS_DEV_LOGIN=\
    $(shell grep -E '^HFS_DEV_LOGIN=' \
	$(BATOCERA_EMULATIONSTATION_PKGDIR)/keys.txt | cut -d = -f 2-)

BATOCERA_EMULATIONSTATION_CONF_OPTS += \
    $(if $(BATOCERA_EMULATIONSTATION_KEY_SCREENSCRAPER_DEV_LOGIN),\
        "-DSCREENSCRAPER_DEV_LOGIN=$(BATOCERA_EMULATIONSTATION_KEY_SCREENSCRAPER_DEV_LOGIN)")
BATOCERA_EMULATIONSTATION_CONF_OPTS += \
    $(if $(BATOCERA_EMULATIONSTATION_KEY_GAMESDB_APIKEY),\
        "-DGAMESDB_APIKEY=$(BATOCERA_EMULATIONSTATION_KEY_GAMESDB_APIKEY)")
BATOCERA_EMULATIONSTATION_CONF_OPTS += \
    $(if $(BATOCERA_EMULATIONSTATION_KEY_CHEEVOS_DEV_LOGIN),\
        "-DCHEEVOS_DEV_LOGIN=$(BATOCERA_EMULATIONSTATION_KEY_CHEEVOS_DEV_LOGIN)")
BATOCERA_EMULATIONSTATION_CONF_OPTS += \
    $(if $(BATOCERA_EMULATIONSTATION_KEY_HFS_DEV_LOGIN),\
        "-DHFS_DEV_LOGIN=$(BATOCERA_EMULATIONSTATION_KEY_HFS_DEV_LOGIN)")

define BATOCERA_EMULATIONSTATION_RPI_FIXUP
	$(SED) 's|.{CMAKE_FIND_ROOT_PATH}/opt/vc|$(STAGING_DIR)/usr|g' $(@D)/CMakeLists.txt
	$(SED) 's|.{CMAKE_FIND_ROOT_PATH}/usr|$(STAGING_DIR)/usr|g'    $(@D)/CMakeLists.txt
endef

# Brands the native Start/Space menu "HOME" instead of "MAIN MENU" - see batocera-home, which
# brands the in-game Guide-button/pause menu the same way, so both read as one system even
# though EmulationStation still does all the actual menu work here (settings, scraper, network,
# etc.) completely unchanged.
define BATOCERA_EMULATIONSTATION_HOME_MENU_TITLE
	$(SED) 's|_("MAIN MENU")|_("HOME")|' $(@D)/es-app/src/guis/GuiMenu.cpp
endef

# Repoints the HOME menu's Kodi entry to Stremio (see package/batocera/utils/stremio), which
# replaces Kodi on this fork. Rather than rename ApiSystem::launchKodi/ScriptId::KODI, this just
# repurposes them in place - isScriptingSupported(KODI) already does a plain file-existence check
# ("kodi" under /usr/bin), so pointing that same check at "batocera-stremio" keeps the entry
# runtime-gated exactly like Kodi's was (hidden on targets where the desktop-apps container isn't
# built, e.g. non-x86_64), with no new ApiSystem method or ES CMake flag needed. The entry itself
# is pulled out of its old #ifdef _ENABLE_KODI_ guard so it no longer depends on Kodi's own
# Buildroot package selection (gone), and the "kodi.enabled" settings toggle is dropped since
# Stremio has no equivalent - everything else under _ENABLE_KODI_ (the startup launcher in
# main.cpp, the "ENABLE KODI"/"LAUNCH KODI AT BOOT" settings switches) is left alone and simply
# compiles out now that nothing selects BR2_PACKAGE_KODI/KODI21 anymore.
define BATOCERA_EMULATIONSTATION_STREMIO_MENU
	$(SED) '/^#ifdef _ENABLE_KODI_$$/{N;s|^#ifdef _ENABLE_KODI_\n\tif (SystemConf::getInstance()->getBool("kodi.enabled", true) && ApiSystem::getInstance()->isScriptingSupported(ApiSystem::KODI))$$|\tif (ApiSystem::getInstance()->isScriptingSupported(ApiSystem::KODI))|}' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) 's|addEntry(_("KODI MEDIA CENTER").c_str(), false, \[this\]|addEntry(_("STREMIO").c_str(), false, [this]|' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) 's|LOG(LogWarning) << "Shutdown terminated with non-zero result!";|LOG(LogWarning) << "Stremio terminated with non-zero result!";|' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) '/^\t}, "iconKodi");$$/{N;s|}, "iconKodi");\n#endif|}, "iconKodi");|}' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) 's|executables.push_back("kodi");|executables.push_back("batocera-stremio");|' $(@D)/es-app/src/ApiSystem.cpp
	$(SED) 's|"batocera-kodi " + commandline|"batocera-stremio " + commandline|' $(@D)/es-app/src/ApiSystem.cpp
endef

# Panthera ships exactly one theme (es-theme-panthera, see package/batocera/emulationstation -
# unconditionally selected, never a choice) - so the "THEME SET" dropdown that lets you switch
# between installed sets, and its save-func that re-applies one, are both meaningless here, and
# the "THEMES" online installer/browser (GuiThemeInstaller) would only ever offer to replace the
# one theme this build ships with something unsupported. Both are removed outright rather than
# left as a read-only label - there's nothing for Appearance settings to say about theme choice
# when there isn't one. THEME CONFIGURATION (the active theme's own subsets/grid/gamelist-style
# options) is left alone - that's tuning the one theme we ship, not picking between sets - so its
# one surviving reference to the removed dropdown just passes nullptr instead, which is exactly
# what that function already treats as "no dropdown involved".
define BATOCERA_EMULATIONSTATION_THEME_LOCK
	$(SED) '/^\t\/\/ Themes installer\/browser$$/,/^\t}$$/d' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) '/^\t\tauto selectedSet = themeSets.find(Settings::getInstance()->getString("ThemeSet"));$$/,/^\t\t\/\/\ttheme_set->add(it->first, it->first, it == selectedSet);$$/d' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) '/^\t\ts->addWithLabel(_("THEME SET"), theme_set);$$/d' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) '/^\t\ts->addSaveFunc(\[s, theme_set, pthis, window, system\]$$/,/^\t\t});$$/d' $(@D)/es-app/src/guis/GuiMenu.cpp
	$(SED) 's|s->addSubMenu(_("THEME CONFIGURATION"), \[this, s, theme_set\]() { openThemeConfiguration(mWindow, s, theme_set); });|s->addSubMenu(_("THEME CONFIGURATION"), [this, s]() { openThemeConfiguration(mWindow, s, nullptr); });|' $(@D)/es-app/src/guis/GuiMenu.cpp
endef

define BATOCERA_EMULATIONSTATION_EXTERNAL_POS
	cp $(STAGING_DIR)/usr/share/batocera-es-system/es_external_translations.h \
	    $(STAGING_DIR)/usr/share/batocera-es-system/es_keys_translations.h $(@D)/es-app/src
	for P in $(STAGING_DIR)/usr/share/batocera-es-system/locales/*; do \
		if test -e $$P/batocera-es-system.po; then \
			cp $(@D)/locale/lang/$$(basename $$P)/LC_MESSAGES/emulationstation2.po \
				$(@D)/locale/lang/$$(basename $$P)/LC_MESSAGES/emulationstation2.po.tmp; \
			$(HOST_DIR)/bin/msgcat \
				$(@D)/locale/lang/$$(basename $$P)/LC_MESSAGES/emulationstation2.po.tmp \
				$$P/batocera-es-system.po > \
				$(@D)/locale/lang/$$(basename $$P)/LC_MESSAGES/emulationstation2.po; \
		fi; \
	done
endef

define BATOCERA_EMULATIONSTATION_RESOURCES
	$(INSTALL) -m 0755 -d $(TARGET_DIR)/usr/share/emulationstation/resources/help
	$(INSTALL) -m 0755 -d $(TARGET_DIR)/usr/share/emulationstation/resources/flags
	$(INSTALL) -m 0755 -d $(TARGET_DIR)/usr/share/emulationstation/resources/battery
	$(INSTALL) -m 0755 -d $(TARGET_DIR)/usr/share/emulationstation/resources/services
	$(INSTALL) -m 0755 -d $(TARGET_DIR)/usr/share/emulationstation/resources/shaders
	$(INSTALL) -m 0755 -d $(TARGET_DIR)/usr/share/emulationstation/resources/shaders/kawase
	$(INSTALL) -m 0644 -D $(@D)/resources/*.* \
	    $(TARGET_DIR)/usr/share/emulationstation/resources
	$(INSTALL) -m 0644 -D $(@D)/resources/help/*.* \
	    $(TARGET_DIR)/usr/share/emulationstation/resources/help
	$(INSTALL) -m 0644 -D $(@D)/resources/flags/*.* \
	    $(TARGET_DIR)/usr/share/emulationstation/resources/flags
	$(INSTALL) -m 0644 -D $(@D)/resources/battery/*.* \
	    $(TARGET_DIR)/usr/share/emulationstation/resources/battery
	$(INSTALL) -m 0644 -D $(@D)/resources/shaders/*.* \
	    $(TARGET_DIR)/usr/share/emulationstation/resources/shaders
	$(INSTALL) -m 0644 -D $(@D)/resources/shaders/*.* \
	    $(TARGET_DIR)/usr/share/emulationstation/resources/shaders/kawase

       # ID3v2 lib
       mkdir -p $(TARGET_DIR)/usr/lib
       $(INSTALL) -m 0644 $(@D)/libid3v2lib.so $(TARGET_DIR)/usr/lib

	# es_input.cfg
	mkdir -p $(TARGET_DIR)/usr/share/batocera/datainit/system/configs/emulationstation
	cp $(BATOCERA_EMULATIONSTATION_PKGDIR)/controllers/es_input.cfg \
	    $(TARGET_DIR)/usr/share/emulationstation

	# savestates config
	$(INSTALL) -m 0644 $(BATOCERA_EMULATIONSTATION_PKGDIR)/es_savestates.cfg \
	    $(TARGET_DIR)/usr/share/emulationstation

	# hooks
	cp $(BATOCERA_EMULATIONSTATION_PKGDIR)/batocera-preupdate-gamelists-hook \
	    $(TARGET_DIR)/usr/bin/
endef

### S31emulationstation
# default for most of architectures
BATOCERA_EMULATIONSTATION_PREFIX = SDL_NOMOUSE=1
BATOCERA_EMULATIONSTATION_CMD = emulationstation-standalone
BATOCERA_EMULATIONSTATION_ARGS = $${EXTRA_OPTS}
BATOCERA_EMULATIONSTATION_POSTFIX = \&

# disabling cec. causing perf issue on init/deinit
#ifeq ($(BR2_PACKAGE_BATOCERA_TARGET_RK3128),y)
BATOCERA_EMULATIONSTATION_CONF_OPTS += -DCEC=OFF
#else
#BATOCERA_EMULATIONSTATION_CONF_OPTS += -DCEC=ON
#endif

## on x86/x86_64: startx runs ES
ifeq ($(BR2_PACKAGE_XSERVER_XORG_SERVER),y)
BATOCERA_EMULATIONSTATION_PREFIX =
BATOCERA_EMULATIONSTATION_CMD = startx
BATOCERA_EMULATIONSTATION_ARGS = --windowed
BATOCERA_EMULATIONSTATION_POST_INSTALL_IMAGES_HOOKS += BATOCERA_EMULATIONSTATION_XORG
endif

ifeq ($(BR2_PACKAGE_BATOCERA_WAYLAND_LABWC),y)
BATOCERA_EMULATIONSTATION_CMD = labwc-launch
BATOCERA_EMULATIONSTATION_DEPENDENCIES += labwc
BATOCERA_EMULATIONSTATION_POST_INSTALL_TARGET_HOOKS += BATOCERA_EMULATIONSTATION_WAYLAND_LABWC
endif

define BATOCERA_EMULATIONSTATION_XORG
	$(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/xorg/xinitrc \
	    $(BINARIES_DIR)/batocera-target/etc/X11/xinit/xinitrc
endef

define BATOCERA_EMULATIONSTATION_WAYLAND_LABWC
    mkdir -p $(TARGET_DIR)/usr/share/labwc
	$(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/wayland/labwc/04-labwc.sh \
	    $(TARGET_DIR)/etc/profile.d/04-labwc.sh
	$(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/wayland/labwc/rc.xml \
	    $(TARGET_DIR)/usr/share/labwc/rc.xml
	$(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/wayland/labwc/S14labwc \
	    $(TARGET_DIR)/etc/init.d/S14labwc
    $(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/wayland/labwc/autostart \
	    $(TARGET_DIR)/usr/share/labwc/autostart
    $(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/wayland/labwc/autostart_* \
	    $(TARGET_DIR)/usr/share/labwc/
    $(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/wayland/labwc/labwc-launch \
	    $(TARGET_DIR)/usr/bin/labwc-launch
endef

define BATOCERA_EMULATIONSTATION_BOOT
	$(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/S31emulationstation \
	    $(TARGET_DIR)/etc/init.d/S31emulationstation
	$(INSTALL) -D -m 0755 $(BATOCERA_EMULATIONSTATION_PKGDIR)/emulationstation-standalone \
	    $(TARGET_DIR)/usr/bin/emulationstation-standalone
	sed -i -e 's;%BATOCERA_EMULATIONSTATION_PREFIX%;${BATOCERA_EMULATIONSTATION_PREFIX};g' \
		-e 's;%BATOCERA_EMULATIONSTATION_CMD%;${BATOCERA_EMULATIONSTATION_CMD};g' \
		-e 's;%BATOCERA_EMULATIONSTATION_ARGS%;${BATOCERA_EMULATIONSTATION_ARGS};g' \
		-e 's;%BATOCERA_EMULATIONSTATION_POSTFIX%;${BATOCERA_EMULATIONSTATION_POSTFIX};g' \
		$(TARGET_DIR)/usr/bin/emulationstation-standalone
	sed -i -e 's;%BATOCERA_EMULATIONSTATION_PREFIX%;${BATOCERA_EMULATIONSTATION_PREFIX};g' \
		-e 's;%BATOCERA_EMULATIONSTATION_CMD%;${BATOCERA_EMULATIONSTATION_CMD};g' \
		-e 's;%BATOCERA_EMULATIONSTATION_ARGS%;${BATOCERA_EMULATIONSTATION_ARGS};g' \
		-e 's;%BATOCERA_EMULATIONSTATION_POSTFIX%;${BATOCERA_EMULATIONSTATION_POSTFIX};g' \
		$(TARGET_DIR)/etc/init.d/S31emulationstation
endef

BATOCERA_EMULATIONSTATION_PRE_CONFIGURE_HOOKS += BATOCERA_EMULATIONSTATION_RPI_FIXUP
BATOCERA_EMULATIONSTATION_PRE_CONFIGURE_HOOKS += BATOCERA_EMULATIONSTATION_HOME_MENU_TITLE
BATOCERA_EMULATIONSTATION_PRE_CONFIGURE_HOOKS += BATOCERA_EMULATIONSTATION_STREMIO_MENU
BATOCERA_EMULATIONSTATION_PRE_CONFIGURE_HOOKS += BATOCERA_EMULATIONSTATION_THEME_LOCK
BATOCERA_EMULATIONSTATION_PRE_CONFIGURE_HOOKS += BATOCERA_EMULATIONSTATION_EXTERNAL_POS
BATOCERA_EMULATIONSTATION_POST_INSTALL_TARGET_HOOKS += BATOCERA_EMULATIONSTATION_RESOURCES
BATOCERA_EMULATIONSTATION_POST_INSTALL_TARGET_HOOKS += BATOCERA_EMULATIONSTATION_BOOT

$(eval $(cmake-package))
