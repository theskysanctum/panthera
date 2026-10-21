################################################################################
#
# batocera-podman
#
################################################################################

BATOCERA_PODMAN_SOURCE =
BATOCERA_PODMAN_DEPENDENCIES = podman
BATOCERA_PODMAN_EMULATOR_INFO = container-apps.emulator.yml

$(eval $(generic-package))
$(eval $(emulator-info-package))
