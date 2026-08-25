#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test: verify spim binary is installed and can run a MIPS program.
 * This test substantively depends on the spim package (R34). */

int main(void) {
    /* Locate spim binary from package */
    const char *spim = getenv("CONAN_SPIM_BIN");

    /* Locate exceptions handler */
    const char *exc = getenv("CONAN_SPIM_EXCEPTIONS");

    if (!spim || !exc) {
        printf("SKIP: CONAN_SPIM_BIN/CONAN_SPIM_EXCEPTIONS not set\n");
        return 1;
    }

    /* Run spim with the test MIPS program */
    char cmd[1024];
    snprintf(cmd, sizeof(cmd),
             "%s -ef %s -file test_hello.s 2>&1",
             spim, exc);

    /* Execute and normalize return value (R34) */
    int ret = system(cmd);
    if (ret != 0) {
        printf("FAIL: spim exited with status %d\n", ret);
        return 1;
    }

    printf("PASS: spim ran test_hello.s successfully\n");
    return 0;
}
