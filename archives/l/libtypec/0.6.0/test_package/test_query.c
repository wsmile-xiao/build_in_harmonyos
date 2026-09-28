/*
 * test_query.c — second consumer use case for libtypec 0.6.0 on OHOS.
 *
 * Beyond the init/version smoke test (test_libtypec.c), this consumer links
 * against the query API surface and exercises it on a device that has no real
 * Type-C controller. It proves:
 *   1. the packaged headers + shared library resolve MULTIPLE exported symbols
 *      (libtypec_get_capability, libtypec_get_conn_capability) — not just
 *      init/exit;
 *   2. the library degrades gracefully when the sysfs nodes are absent/invalid
 *      (returns an error code rather than crashing / segfaulting), which is the
 *      relevant robustness property on a hardware-less OHOS box.
 * We do NOT assert the numeric return values (they depend on hardware); the
 * assertion is "the process reaches the end and exits 0".
 */
#include <stdio.h>
#include <string.h>

#include "libtypec.h"

int main(void)
{
    char *session[LIBTYPEC_SESSION_MAX_INDEX] = {0};

    int init_ret = libtypec_init(session, LIBTYPEC_BACKEND_SYSFS);
    if (session[LIBTYPEC_VERSION_INDEX] == NULL) {
        fprintf(stderr, "FAIL: init did not populate version string\n");
        return 1;
    }

    struct libtypec_capability_data cap;
    memset(&cap, 0, sizeof(cap));
    int r1 = libtypec_get_capability(&cap);

    struct libtypec_connector_cap_data conn_cap;
    memset(&conn_cap, 0, sizeof(conn_cap));
    /* connector number 0 almost certainly does not exist on this device;
     * the call must return an error, not dereference a NULL node. */
    int r2 = libtypec_get_conn_capability(0, &conn_cap);

    printf("query consumer OK: init_ret=%d get_capability=%d get_conn_cap(0)=%d "
           "(negative values are expected without Type-C hardware; "
           "what matters is that no crash occurred)\n",
           init_ret, r1, r2);

    libtypec_exit();
    return 0;
}
