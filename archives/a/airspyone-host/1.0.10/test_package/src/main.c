#include <stdio.h>
#include "libairspy/airspy.h"

int main(void) {
    airspy_lib_version_t ver;
    airspy_lib_version(&ver);
    printf("AirSpy lib version: %d.%d.%d\n", ver.major_version, ver.minor_version, ver.revision);
    /* Also check the version string macro */
    printf("AIRSPY_VERSION: %s\n", AIRSPY_VERSION);
    return 0;
}
