/* test.c — consumer test for srs-state (libst) 1.9.5.
 * Actually exercises the State Threads API: scheduler init, coroutine
 * creation/join, argument passing, and cooperative scheduling (R34).
 */
#include "st.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int worker_count = 0;
static int worker_sum = 0;

static void *add_worker(void *arg)
{
    long value = (long)(intptr_t)arg;
    worker_sum += (int)value;
    worker_count++;
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
    st_thread_t t1, t2, t3;
    void *join_result = NULL;
    int checked = 0;
    st_utime_t before, after;

    if (!require_true(st_init() == 0, "st_init starts the scheduler"))
        return EXIT_FAILURE;
    checked++;

    if (!require_true(st_thread_self() != NULL, "main coroutine handle"))
        return EXIT_FAILURE;
    checked++;

    t1 = st_thread_create(add_worker, (void *)(intptr_t)10, 1, 0);
    t2 = st_thread_create(add_worker, (void *)(intptr_t)32, 1, 0);
    t3 = st_thread_create(add_worker, (void *)(intptr_t)100, 1, 0);
    if (!require_true(t1 && t2 && t3, "coroutine creation (joinable)"))
        return EXIT_FAILURE;
    checked++;

    if (!require_true(st_thread_join(t1, &join_result) == 0 &&
                      st_thread_join(t2, NULL) == 0 &&
                      st_thread_join(t3, NULL) == 0,
                      "coroutines joined"))
        return EXIT_FAILURE;
    checked++;

    if (!require_true(worker_count == 3, "all workers ran"))
        return EXIT_FAILURE;
    checked++;
    if (!require_true(worker_sum == 142, "arguments passed and accumulated (10+32+100)"))
        return EXIT_FAILURE;
    checked++;

    /* Cooperative scheduling: st_utime(0) yields without real delay. */
    before = st_utime();
    st_usleep(0);
    after = st_utime();
    if (!require_true(after >= before, "monotonic microsecond clock via st_utime"))
        return EXIT_FAILURE;
    checked++;

    printf("PASS: srs-state 1.9.5 consumer API test (%d assertions)\n", checked);
    return EXIT_SUCCESS;
}
