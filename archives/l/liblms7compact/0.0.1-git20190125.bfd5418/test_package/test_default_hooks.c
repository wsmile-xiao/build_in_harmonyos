/*
 * test_liblms7compact_default_hooks — HarmonyOS adaptation check.
 *
 * This adaptation adds lms7_defaults.c, which provides WEAK default
 * implementations of the upstream platform hooks (lms7_spi_transact /
 * lms7_spi_post / lms7_log_ex) so the library can be built and linked
 * as a standalone shared/static object without hardware integration.
 *
 * This test intentionally does NOT override the hooks.  Linking
 * successfully proves the weak defaults satisfy the linker; calling
 * lms7_reset() and observing the expected error return proves the
 * default hook path is really taken (no hardware → no SPI transport).
 */
#include "liblms7002m.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            printf("FAIL: %s\n", msg);                                      \
            failures++;                                                     \
        }                                                                   \
    } while (0)

int main(void)
{
    struct lms7_state st;
    int r;

    memset(&st, 0, sizeof(st));
    st.fref = 100000000u;

    /* Default weak hooks are linked in; without an SPI transport the
       library must report failure instead of crashing. */
    r = lms7_reset(&st);
    CHECK(r != LMSE_OK, "default hook path: lms7_reset reports no-SPI error");

    if (failures == 0) {
        printf("test_liblms7compact_default_hooks: ALL TESTS PASSED\n");
        return 0;
    }
    printf("test_liblms7compact_default_hooks: %d FAILURES\n", failures);
    return 1;
}
