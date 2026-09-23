/* libbdplus test_package — consumer checks against the packaged library.
 *
 * Proves, against the installed libbdplus (shared or static):
 *  1. runtime version is 0.2.0 (matches upstream 0.2.0 source)
 *  2. compile-time version macros match the runtime version (headers
 *     and library come from the same build, not stubbed)
 *  3. NULL-handle guards behave as documented (-1, no crash)
 *  4. bdplus_init on a nonexistent disc path fails gracefully with NULL
 *     (exercises libgcrypt init + config load + file layer; never
 *     touches a real disc) and bdplus_free(NULL) is safe
 *
 * Each passing check prints one "CHECK-OK: <name>" line; the test_package
 * conanfile counts those lines for the HMBS_TEST_PACKAGE_RESULT marker.
 * Exit code is 0 only if all 4 checks pass (exit-0-alone is not proof).
 */
#include <libbdplus/bdplus.h>
#include <libbdplus/bdplus-version.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    int major = -1, minor = -1, micro = -1;
    static const uint8_t vid[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    bdplus_t *plus;

    bdplus_get_version(&major, &minor, &micro);
    printf("libbdplus runtime version=%d.%d.%d\n", major, minor, micro);
    if (major != 0 || minor != 2 || micro != 0) {
        fprintf(stderr, "FAIL: unexpected version (want 0.2.0)\n");
        return 1;
    }
    printf("CHECK-OK: version-0.2.0\n");

    printf("libbdplus macro version=%d.%d.%d\n",
           BDPLUS_VERSION_MAJOR, BDPLUS_VERSION_MINOR, BDPLUS_VERSION_MICRO);
    if (BDPLUS_VERSION_MAJOR != major || BDPLUS_VERSION_MINOR != minor ||
        BDPLUS_VERSION_MICRO != micro) {
        fprintf(stderr, "FAIL: macro/runtime version mismatch\n");
        return 1;
    }
    if (strcmp(BDPLUS_VERSION_STRING, "0.2.0") != 0) {
        fprintf(stderr, "FAIL: BDPLUS_VERSION_STRING != 0.2.0\n");
        return 1;
    }
    printf("CHECK-OK: version-macro-match\n");

    if (bdplus_get_code_gen(NULL) != -1 ||
        bdplus_get_code_date(NULL) != -1 ||
        bdplus_is_cached(NULL) != -1) {
        fprintf(stderr, "FAIL: NULL-handle guard misbehaved\n");
        return 1;
    }
    printf("CHECK-OK: null-handle-guards\n");

    /* No such disc: must fail gracefully with NULL (and must not crash
     * while trying). A non-NULL return here would mean the error path
     * is broken, so fail loudly instead of silently passing. */
    plus = bdplus_init("/nonexistent-bdplus-disc-0", NULL, vid);
    if (plus != NULL) {
        fprintf(stderr, "FAIL: bdplus_init on bogus path unexpectedly succeeded\n");
        bdplus_free(plus);
        return 1;
    }
    bdplus_free(NULL);
    printf("CHECK-OK: init-rejects-bad-path\n");

    printf("libbdplus consumer test PASS (4/4)\n");
    return 0;
}
