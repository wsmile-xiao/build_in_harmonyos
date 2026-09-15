/* test_dcap.c — dcap 2.47.14 consumer test (R34: real API calls only).
 *
 * Exercises offline-safe public APIs from <dcap.h>, all verified against
 * the 2.47.14 sources (configure.ac protocol/major/minor defines and
 * src/dcap_error.c dc_strerror fallback). No dCache server is contacted:
 * every network API (dc_open/dc_stat/...) is intentionally untouched.
 */
/* musl/OHOS provides off64_t/stat64/dirent64 only under
 * _GNU_SOURCE/_LARGEFILE64_SOURCE; define before any system header so a
 * bare consumer TU sees the same aliases as the library build. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#ifndef _LARGEFILE64_SOURCE
#define _LARGEFILE64_SOURCE 1
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dcap.h>

static int failures;
static int checks;

#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        fprintf(stderr, "check failed at %s:%d: %s\n", __FILE__, __LINE__, #condition); \
        ++failures; \
    } \
} while (0)

int main(void)
{
    const char *patch;
    const char *version;

    /* Protocol generation pinned by configure.ac dcap_major_version = 2. */
    CHECK(dc_getProtocol() == 2);
    /* Library version pinned by configure.ac: 47.14. */
    CHECK(dc_getMajor() == 47);
    CHECK(dc_getMinor() == 14);
    patch = dc_getPatch();
    CHECK(patch != NULL);
    version = getDcapVersion();
    CHECK(version != NULL);
    /* dcap_errno index 0 is "OK"; out-of-range yields "Unknown error". */
    CHECK(dc_strerror(0) != NULL);
    CHECK(strcmp(dc_strerror(99999), "Unknown error") == 0);

    /* Exercise void setters to prove link + runtime init (not counted). */
    dc_setDebugLevel(0);
    dc_setOnError(onErrorFail);
    dc_resetExtraOption();

    printf("dcap API checks: %d/%d passed (lib version %d.%d, protocol %d)\n",
           checks - failures, checks,
           dc_getMajor(), dc_getMinor(), dc_getProtocol());
    if (failures != 0) {
        fprintf(stderr, "%d dcap API checks failed\n", failures);
        return EXIT_FAILURE;
    }
    puts("dcap consumer checks passed");
    return EXIT_SUCCESS;
}
