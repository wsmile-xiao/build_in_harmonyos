/*
 * test_libtypec.c — consumer smoke test for libtypec 0.6.0 on OHOS.
 *
 * Real Type-C hardware (and /sys/class/typec) does not exist on the OHOS
 * build device, so we do not assert on connector data. What this test proves:
 *   1. the packaged headers are consumable and the consumer links against
 *      libtypec (and transitively libudev from eudev);
 *   2. the signed shared object is accepted by the OHOS loader;
 *   3. libtypec_init() actually executes the library code path — it populates
 *      session[LIBTYPEC_VERSION_INDEX] with "libtypec <ver>" *before* it
 *      probes the (absent) sysfs backend, so that string is deterministic and
 *      hardware-independent.
 */
#include <stdio.h>
#include <string.h>

#include "libtypec.h"

int main(void)
{
    char *session[LIBTYPEC_SESSION_MAX_INDEX] = {0};

    int ret = libtypec_init(session, LIBTYPEC_BACKEND_SYSFS);

    /* On a Type-C-less OHOS box the sysfs backend init returns a negative
     * value; that is expected and NOT a test failure. The version string is
     * set before the backend is probed. */
    if (session[LIBTYPEC_VERSION_INDEX] == NULL) {
        fprintf(stderr, "FAIL: libtypec_init did not set session version string\n");
        return 1;
    }
    if (strncmp(session[LIBTYPEC_VERSION_INDEX], "libtypec ", 9) != 0) {
        fprintf(stderr, "FAIL: unexpected version string: '%s'\n",
                session[LIBTYPEC_VERSION_INDEX]);
        return 1;
    }
    /* kernel/os strings are informational: uname may succeed but OHOS has no
     * /etc/os-release, so get_os_name() returns NULL. Do not fail on these. */
    const char *kernel = session[LIBTYPEC_KERNEL_INDEX] ? session[LIBTYPEC_KERNEL_INDEX] : "(n/a)";
    const char *os = session[LIBTYPEC_OS_INDEX] ? session[LIBTYPEC_OS_INDEX] : "(n/a)";

    printf("libtypec OK: version='%s' kernel='%s' os='%s' (backend ret=%d, "
           "expected nonzero on hardware-less OHOS)\n",
           session[LIBTYPEC_VERSION_INDEX], kernel, os, ret);

    libtypec_exit();
    return 0;
}
