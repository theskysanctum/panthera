################################################################################
#
# batocera-qemu
#
################################################################################

BATOCERA_QEMU_SOURCE =
BATOCERA_QEMU_DEPENDENCIES = qemu
BATOCERA_QEMU_EMULATOR_INFO = qemu.emulator.yml

$(eval $(generic-package))
$(eval $(emulator-info-package))
