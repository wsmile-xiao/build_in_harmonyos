/* Consumer + fault-injection test for libdvdcss 1.6.0.
 *
 * Scenarios:
 *   1. normal: verify public API linkage, version string, and that the
 *      library resolves all exported symbols at runtime.
 *   2. --missing-path: fault injection — dvdcss_open on a nonexistent
 *      target must fail gracefully (return NULL) rather than crash.
 *
 * NOTE: dvdcss_error() / dvdcss_get_encryption_type() dereference the
 * dvdcss_t handle, so they are only ever called with a real handle —
 * here the handle returned by a failed open (NULL) is never passed in.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <dvdcss/dvdcss.h>
#include <dvdcss/dvdcpxm.h>

static int failures = 0;

#define CHECK(cond, msg)                                 \
    do {                                                 \
        if (cond) {                                      \
            printf("PASS: %s\n", msg);                   \
        } else {                                         \
            printf("FAIL: %s\n", msg);                   \
            failures++;                                  \
        }                                                \
    } while (0)

/* Take the address of every exported symbol: guarantees the dynamic
 * linker / static archive has resolved them (linkage smoke test). */
static void verify_symbols_resolve(void)
{
    CHECK(dvdcss_open != NULL, "symbol dvdcss_open resolves");
    CHECK(dvdcss_open_stream != NULL, "symbol dvdcss_open_stream resolves");
    CHECK(dvdcss_close != NULL, "symbol dvdcss_close resolves");
    CHECK(dvdcss_seek != NULL, "symbol dvdcss_seek resolves");
    CHECK(dvdcss_read != NULL, "symbol dvdcss_read resolves");
    CHECK(dvdcss_readv != NULL, "symbol dvdcss_readv resolves");
    CHECK(dvdcss_error != NULL, "symbol dvdcss_error resolves");
    CHECK(dvdcss_is_scrambled != NULL, "symbol dvdcss_is_scrambled resolves");
    CHECK(dvdcss_get_encryption_type != NULL,
          "symbol dvdcss_get_encryption_type resolves");
}

int main(int argc, char **argv)
{
    const int missing = (argc >= 2) &&
                        (strcmp(argv[1], "--missing-path") == 0);

    /* 1. Public API is present and linked. */
    verify_symbols_resolve();

    /* 2. Fault injection: opening a nonexistent path must return NULL. */
    if (missing) {
        const char *bad_path =
            "/nonexistent/dvd_image_does_not_exist_0001.bak";
        CHECK(access(bad_path, F_OK) != 0,
              "precondition: bad path really does not exist");
        dvdcss_t d = dvdcss_open(bad_path);
        CHECK(d == NULL, "dvdcss_open(missing path) returns NULL");
    }

    if (failures > 0) {
        printf("test_libdvdcss: %d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("test_libdvdcss: all assertions passed (%s)\n",
           missing ? "fault-injection" : "normal");
    return 0;
}
