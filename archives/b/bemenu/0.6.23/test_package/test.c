#include <stdio.h>
#include "bemenu.h"

int main(void) {
    const char *ver = bm_version();
    if (ver && ver[0]) {
        printf("bemenu version: %s\n", ver);
        return 0;
    }
    fprintf(stderr, "ERROR: bm_version() returned NULL or empty\n");
    return 1;
}
