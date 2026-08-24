#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34: test must depend on the tested package.
     * pkill is a CLI tool — execute pkill -V and verify exit code. */
    int rc = system("pkill -V");
    if (rc != 0) {
        fprintf(stderr, "pkill -V failed with exit code %d\n", rc);
        return 1;
    }
    printf("pkill binary responds to -V: OK\n");
    return 0;
}
