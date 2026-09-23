#include <stdio.h>
#include <stdlib.h>
#include "openscap/oscap.h"

int main(void) {
    oscap_init();
    const char *ver = oscap_get_version();
    if (ver && ver[0]) {
        printf("openscap version: %s\n", ver);
        oscap_cleanup();
        return 0;
    }
    fprintf(stderr, "Failed to get openscap version\n");
    oscap_cleanup();
    return 1;
}
