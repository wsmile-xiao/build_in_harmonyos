/* Conan test_package for xine-lib/1.2.13 (libxine) — HarmonyOS PC.
 *
 * Two jobs:
 *   1. consumer-side smoke test of the public libxine API (xine_new/xine_init/
 *      xine_get_version_string/xine_check_version/xine_exit), i.e. the test
 *      really calls into the packaged library (R34);
 *   2. OHOS-specific assertions (>=1 required by the adaptation contract):
 *      the toolchain must define __OHOS__ and must not pull in glibc-only
 *      headers, proving the package was really built for OpenHarmony/musl.
 */
#include <stdio.h>
#include <string.h>

#include <xine.h>

static int failures = 0;
static int assertions = 0;

#define CHECK(cond, msg)                                \
    do {                                                \
        ++assertions;                                   \
        if (cond) {                                     \
            printf("PASS: %s\n", (msg));                \
        } else {                                        \
            printf("FAIL: %s\n", (msg));                \
            ++failures;                                 \
        }                                               \
    } while (0)

int main(void)
{
    /* ---------- OHOS-specific test case ---------- */
#if defined(__OHOS__)
    CHECK(1, "OHOS: toolchain defines __OHOS__ (native aarch64-linux-ohos build)");
#else
    CHECK(0, "OHOS: toolchain defines __OHOS__ (native aarch64-linux-ohos build)");
#endif
#if defined(__GLIBC__)
    CHECK(0, "OHOS: glibc headers are not in use (musl libc expected)");
#else
    CHECK(1, "OHOS: glibc headers are not in use (musl libc expected)");
#endif

    /* ---------- consumer-side public API smoke test ---------- */
    xine_t *xine = xine_new();
    CHECK(xine != NULL, "xine_new() returns an engine handle");
    if (!xine) {
        printf("\n%d/%d assertions passed, %d failed\n",
               assertions - failures, assertions, failures);
        return 1;
    }

    xine_init(xine);

    const char *version = xine_get_version_string();
    CHECK(version != NULL, "xine_get_version_string() returns a string");
    CHECK(version && strstr(version, "1.2.") != NULL,
          "linked libxine reports the 1.2.x series");
    if (version)
        printf("      linked libxine version: %s\n", version);

    int major = 0, minor = 0, sub = 0;
    xine_get_version(&major, &minor, &sub);
    CHECK(major == 1 && minor == 2 && sub == 13,
          "xine_get_version() reports 1.2.13");

    CHECK(xine_check_version(1, 2, 13) == 1,
          "xine_check_version(1,2,13) reports an ABI-compatible library");

    xine_exit(xine);
    CHECK(1, "xine_exit() releases the engine without crashing");

    printf("\n%d/%d assertions passed, %d failed\n",
           assertions - failures, assertions, failures);
    return failures ? 1 : 0;
}
