/*
 * test_afl.c — afl test_package "fuzz target".
 *
 * Reads stdin and performs deterministic byte processing (accumulating a
 * digest). Exits 0 on any input. It is driven by the afl tools in the
 * test_package smoke runs: afl-showmap forks it, afl-fuzz -n mutates its
 * stdin in dumb mode. It does not link against afl — afl is a tool
 * package (no library); the tools themselves are what the test exercises.
 */
#include <stdio.h>

int main(void) {
    int c;
    unsigned long acc = 0;
    unsigned char buf[256];
    size_t len = 0;

    while ((c = getchar()) != EOF) {
        if (len < sizeof(buf)) {
            buf[len++] = (unsigned char)c;
        }
        acc = acc * 31 + (unsigned char)c;
    }

    /* Deterministic digest so the optimizer cannot remove the work. */
    fprintf(stderr, "digest=%lx len=%zu\n", acc, len);
    return 0;
}
