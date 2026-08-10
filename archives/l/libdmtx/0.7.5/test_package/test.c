#include <stdio.h>
#include "dmtx.h"

int main(void) {
    char *version = dmtxVersion();
    if (version == NULL) {
        fprintf(stderr, "Error: dmtxVersion() returned NULL\n");
        return 1;
    }
    printf("libdmtx version: %s\n", version);
    return 0;
}
