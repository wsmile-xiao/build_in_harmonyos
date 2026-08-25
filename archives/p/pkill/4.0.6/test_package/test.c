#include <stdio.h>
#include <stdlib.h>

#ifndef PKILL_BIN
#define PKILL_BIN "pkill"
#endif

int main(void) {
    /* R34: test must depend on the tested package.
     * Execute pkill -V via full path (passed from CMake definition)
     * and verify exit code. */
    int rc = system(PKILL_BIN " -V");
    if (rc != 0) {
        fprintf(stderr, "pkill -V failed with exit code %d\n", rc);
        return 1;
    }
    printf("pkill binary responds to -V: OK\n");
    return 0;
}
