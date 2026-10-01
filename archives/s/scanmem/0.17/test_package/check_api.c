/*
 * check_api.c -- link-time consumer of the packaged libscanmem.
 *
 * Unlike check_libscanmem.c (which resolves symbols at run time via dlopen),
 * this translation unit is *compiled and linked* against the packaged headers
 * and shared library. That is what makes the test_package a real consumer:
 *
 *   - it proves <scanmem/scanmem.h> is self-contained and installable;
 *   - it proves lib/libscanmem.so(.1) exports the public sm_* API;
 *   - and it gives the CI L1e destructive negative test (R34) a hard
 *     dependency to bite on. L1e moves bin/, lib/ and include/ out of the
 *     package folder and re-runs `conan test`; if the artifacts are really
 *     required, the link below fails and the test fails, which is the
 *     behaviour L1e asserts. A test_package whose build() ignores the package
 *     would pass L1e's sabotage and be reported as a fake test.
 *
 * Prints "APICHECK version=<v>". Driven by test_scanmem.sh (check t7).
 */

#include <scanmem/scanmem.h>

#include <stdio.h>

int main(void)
{
    const char *ver = sm_get_version();
    if (ver == NULL || ver[0] == '\0') {
        printf("APICHECK version=empty\n");
        return 1;
    }
    printf("APICHECK version=%s\n", ver);

    /* Second entry point, to prove more than one exported symbol resolves. */
    sm_printversion(stdout);
    fputc('\n', stdout);
    return 0;
}
