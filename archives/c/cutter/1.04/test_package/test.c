#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34: Execute the actual cutter binary and verify output */
    int rc = system("cutter 2>&1 | grep -q 'cutter - TCP/IPv4 connection cutter'");
    if (rc == 0) {
        printf("test_cutter: PASS - cutter binary works correctly\n");
        return 0;
    }
    fprintf(stderr, "test_cutter: FAIL - cutter binary not working\n");
    return 1;
}
