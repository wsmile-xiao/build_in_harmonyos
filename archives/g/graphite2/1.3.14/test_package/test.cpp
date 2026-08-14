/*
 * test_package/test.cpp — Consumer test for graphite2 library
 *
 * R34: This test substantively depends on the tested package by calling
 * the gr_engine_version() API to verify the library is linked and functional.
 *
 * Note: graphite2 is a C++ library with a C API. The test must be C++
 * so the C++ runtime (libc++) is linked when using the static library.
 */
#include <cstdio>
#include <graphite2/Font.h>

int main(void) {
    int nMajor = 0, nMinor = 0, nBugFix = 0;
    gr_engine_version(&nMajor, &nMinor, &nBugFix);

    printf("graphite2 engine version: %d.%d.%d\n", nMajor, nMinor, nBugFix);

    /* Verify the version matches expected 1.3.14 */
    if (nMajor != GR2_VERSION_MAJOR || nMinor != GR2_VERSION_MINOR || nBugFix != GR2_VERSION_BUGFIX) {
        fprintf(stderr, "ERROR: version mismatch! Expected %d.%d.%d, got %d.%d.%d\n",
                GR2_VERSION_MAJOR, GR2_VERSION_MINOR, GR2_VERSION_BUGFIX,
                nMajor, nMinor, nBugFix);
        return 1;
    }

    printf("graphite2 test PASSED\n");
    return 0;
}
