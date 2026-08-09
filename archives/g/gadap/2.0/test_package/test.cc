/* test.cc — gadap 2.0 consumer test (Conan L1) */
#include <cstdio>
#include "gadap.h"

int main(void) {
    /* gadap_numopen() returns the number of open datasets; with no
     * network access in CI it must return 0 (not crash, not negative). */
    int n = gadap_numopen();
    if (n != 0) {
        std::fprintf(stderr, "FAIL: gadap_numopen() returned %d (expected 0)\n", n);
        return 1;
    }
    std::printf("gadap_numopen() = %d (expected 0 with no open datasets)\n", n);

    /* gadap_open() with an invalid URL must return a non-success status
     * rather than crashing (validates library linkage + error path). */
    GADAP_DATASET d = -1;
    GADAP_STATUS st = gadap_open("http://127.0.0.1:1/invalid", &d);
    std::printf("gadap_open(invalid) status = %d\n", (int)st);
    if (st == GADAP_SUCCESS) {
        std::fprintf(stderr, "FAIL: gadap_open(invalid) unexpectedly succeeded\n");
        return 1;
    }
    return 0;
}
