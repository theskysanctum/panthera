################################################################################
#
# batocera-splash
#
################################################################################

BATOCERA_SPLASH_VERSION = 6.0
BATOCERA_SPLASH_SOURCE=

BATOCERA_SPLASH_TGVERSION=$(BATOCERA_SYSTEM_VERSION) $(BATOCERA_SYSTEM_DATE)

BATOCERA_SPLASH_DEPENDENCIES += host-imagemagick dejavu

BATOCERA_SPLASH_POST_INSTALL_TARGET_HOOKS += BATOCERA_SPLASH_INSTALL_SCRIPT
BATOCERA_SPLASH_POST_INSTALL_TARGET_HOOKS += BATOCERA_SPLASH_INSTALL_BOOT_LOGO
BATOCERA_SPLASH_POST_INSTALL_TARGET_HOOKS += BATOCERA_SPLASH_INSTALL_IMAGE

define BATOCERA_SPLASH_INSTALL_SCRIPT
    mkdir -p $(TARGET_DIR)/etc/init.d
    install -m 0755 $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/core/batocera-splash/scripts/Ssystem-splash \
        $(TARGET_DIR)/etc/init.d/S03system-splash
    install -m 0755 $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/core/batocera-splash/scripts/Ssplashscreencontrol \
        $(TARGET_DIR)/etc/init.d/S30splashscreencontrol
    install -m 0755 $(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/core/batocera-splash/scripts/Ssplash-image \
        $(TARGET_DIR)/etc/init.d/S28splash
endef

# Ssystem-splash (the very-early framebuffer logo, shown before the splash below even starts)
# always needs this, regardless of the image splash below.
define BATOCERA_SPLASH_INSTALL_BOOT_LOGO
    mkdir -p $(TARGET_DIR)/usr/share/batocera/splash
    cp "$(BR2_EXTERNAL_BATOCERA_PATH)/package/batocera/core/batocera-splash/images/logo.png" \
        "${TARGET_DIR}/usr/share/batocera/splash/boot-logo.png"
endef

# $(1) source image, $(2) point size, $(3) text position, $(4) output image
define BATOCERA_SPLASH_ANNOTATE
    $(HOST_DIR)/bin/magick "$(BATOCERA_SPLASH_PKGDIR)/images/$(1)" \
        -font $(DEJAVU_DIR)/ttf/DejaVuSans.ttf -fill white -pointsize $(2) \
        -annotate $(3) "$(BATOCERA_SPLASH_TGVERSION)" \
        "$(TARGET_DIR)/usr/share/batocera/splash/$(4)"
endef

define BATOCERA_SPLASH_INSTALL_IMAGE
    mkdir -p $(TARGET_DIR)/usr/share/batocera/splash
    $(call BATOCERA_SPLASH_ANNOTATE,logo.png,30,+50+1020,logo-version.png)
    $(call BATOCERA_SPLASH_ANNOTATE,logo-3-2-480-rotate.png,15,270x270+300+440,logo-version-320x480.png)
    $(call BATOCERA_SPLASH_ANNOTATE,logo-16-9-480-rotate.png,20,270x270+440+814,logo-version-480x854.png)
    $(call BATOCERA_SPLASH_ANNOTATE,logo-480p.png,20,+40+440,logo-version-640x480.png)
    $(call BATOCERA_SPLASH_ANNOTATE,logo-240.png,15,+20+220,logo-version-320x240.png)
    $(call BATOCERA_SPLASH_ANNOTATE,logo-480-dmg.png,20,+40+440,logo-version-640x480-dmg.png)
endef

$(eval $(generic-package))
