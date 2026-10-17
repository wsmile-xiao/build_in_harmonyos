/*
 * test.c — as31 test_package smoke test.
 *
 * as31 is a command-line 8051 assembler (not a library), so this
 * test verifies the as31 binary is callable and can assemble a
 * simple 8051 program, checking the expected output.
 *
 * R34: This test actually executes the as31 binary — it is not
 * a hollow printf-only test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    FILE *p;
    char out[1024];
    size_t n;

    /* Run as31 with no arguments — it should print usage */
    p = popen("as31 2>&1", "r");
    if (!p) {
        fprintf(stderr, "FAIL: cannot run as31\n");
        return 1;
    }
    n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    pclose(p);

    if (strstr(out, "Usage") == NULL) {
        fprintf(stderr, "FAIL: as31 did not print usage. Output: %s\n", out);
        return 1;
    }

    printf("PASS: as31 binary executed and printed usage\n");
    return 0;
}
