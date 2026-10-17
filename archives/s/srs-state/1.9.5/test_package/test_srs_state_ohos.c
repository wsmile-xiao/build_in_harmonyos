/* test_srs_state_ohos.c — HarmonyOS consumer test for srs-state (libst) 1.9.5.
 * Validates the OHOS aarch64 adaptation: context-switch assembly (md_linux2.S),
 * scheduler lifecycle, coroutine scheduling, and the monotonic clock on the
 * HarmonyOS PC platform (consumer.ohos.* case).
 */
#include "st.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define OHOS_COROUTINES 4

static int done_count = 0;
static long payload[OHOS_COROUTINES];

static void *ohos_worker(void *arg)
{
    long slot = (long)(intptr_t)arg;
    /* Exercise cooperative yield: every worker yields once before finishing. */
    st_usleep(0);
    payload[slot] = slot * slot;
    done_count++;
    st_thread_exit(NULL);
    return NULL;
}

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void)
{
    st_thread_t workers[OHOS_COROUTINES];
    long i;
    st_utime_t t0, t1;
    int checked = 0;

    /* HarmonyOS PC aarch64 ABI. */
    if (!require_true(sizeof(void *) == 8, "HarmonyOS AArch64 ABI"))
        return EXIT_FAILURE;
    checked++;

    /* OHOS kernel reports "HongMeng Kernel ..." from uname -r; the adaptation
     * must not depend on kernel release string formatting. */
    if (!require_true(system("uname -s > /dev/null 2>&1") == 0,
                      "host system query available"))
        return EXIT_FAILURE;
    checked++;

    if (!require_true(st_init() == 0, "st_init on HarmonyOS scheduler"))
        return EXIT_FAILURE;
    checked++;

    for (i = 0; i < OHOS_COROUTINES; i++) {
        workers[i] = st_thread_create(ohos_worker, (void *)(intptr_t)i, 1, 0);
        if (!require_true(workers[i] != NULL, "OHOS coroutine slot creation")) {
            return EXIT_FAILURE;
        }
    }
    checked++;

    for (i = 0; i < OHOS_COROUTINES; i++) {
        if (!require_true(st_thread_join(workers[i], NULL) == 0,
                          "OHOS coroutine join"))
            return EXIT_FAILURE;
    }
    checked++;

    if (!require_true(done_count == OHOS_COROUTINES, "all OHOS workers completed"))
        return EXIT_FAILURE;
    checked++;
    if (!require_true(payload[0] == 0 && payload[1] == 1 && payload[2] == 4 &&
                      payload[3] == 9,
                      "slot payloads computed after cooperative yields"))
        return EXIT_FAILURE;
    checked++;

    /* Monotonic microsecond clock must strictly move forward across a real
     * sleep (2 ms): t1 == t0 would mean the clock stood still, which is a
     * monotonicity violation, not a pass. */
    t0 = st_utime();
    st_usleep(2000);
    t1 = st_utime();
    if (!require_true(t1 > t0, "st_utime strictly monotonic across 2ms sleep"))
        return EXIT_FAILURE;
    checked++;

    printf("PASS: srs-state 1.9.5 HarmonyOS consumer API test (%d assertions)\n",
           checked);
    return EXIT_SUCCESS;
}
