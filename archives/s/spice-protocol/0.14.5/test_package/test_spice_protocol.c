#include <stdint.h>
#include <stdio.h>

#include <spice/protocol.h>

int main(void)
{
    SpiceLinkHeader header = {
        SPICE_MAGIC,
        SPICE_VERSION_MAJOR,
        SPICE_VERSION_MINOR,
        sizeof(SpiceLinkMess),
    };

    if (header.magic != SPICE_MAGIC) {
        return 1;
    }
    if (header.major_version != 2 || header.minor_version != 2) {
        return 2;
    }
    if (header.size != sizeof(SpiceLinkMess)) {
        return 3;
    }
    if (SPICE_CHANNEL_MAIN != 1) {
        return 4;
    }
    if (SPICE_DISPLAY_CAP_GL_SCANOUT2 <= SPICE_DISPLAY_CAP_GL_SCANOUT) {
        return 5;
    }

    printf(
        "spice-protocol: magic=0x%08x version=%u.%u header=%zu channel-main=%d\n",
        header.magic,
        header.major_version,
        header.minor_version,
        sizeof(header),
        SPICE_CHANNEL_MAIN
    );
    return 0;
}
